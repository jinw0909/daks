# api/webhook.py

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import http.client
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.models import (
    Payment, WebhookLog, WebhookLogHistory
)

from app.api.deps import DbSession
from app.services.websocket_manager import manager

from app.services.webhook_service import (
    find_payment_by_metadata,
    add_payment_history,
    apply_common_payment_fields,
    to_int_or_none,
)




router = APIRouter()
KST = ZoneInfo("Asia/Seoul")
TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")
@router.post(
    "/webhook/toss",
    summary="Toss Webhook",
    tags=["USER API"],
)
async def toss_webhook(
    request: Request,
    db: DbSession,
):

    payload = None
    order_id = None
    payment_key = None
    status = None
    payment_id = None
    product_key = None
    product_name = None
    ticket_user_id = None
    customer_name = None
    event_type = None

    try:

        print("========== Toss Webhook Received ==========")
        payload = await request.json()
        # =====================================
        # 1. Payload parsing
        # =====================================
        event_type = payload.get("eventType")
        data = payload.get("data", {}) or {}
        payment = data.get("payment", {}) or {}
        order_id = payment.get("orderId")

        if event_type == "PAYMENT_STATUS_CHANGED":

            payment_key = data.get("paymentKey")

        else:
            payment_key = payment.get("paymentKey")

        status = payment.get("status")
        method = payment.get("method")
        amount = (data.get("amount")or payment.get("totalAmount"))
        approved_at = payment.get("approvedAt")
        created_at = data.get("createdAt")
        receipt_url = (payment.get("receipt", {}) or {}).get("url")
        meta_fields = (data.get("metaFields", {}) or {})

        payment_id = to_int_or_none(
            meta_fields.get("paymentId")
        )

        ticket_user_id = to_int_or_none(
            meta_fields.get("ticketUserId")
        )
        customer_name = data.get("customerName")
        now_kst = datetime.now(KST)

        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
        )

        order_items = data.get("orderItems", []) or []

        first_order_item = (
            order_items[0]
            if order_items
            else {}
        )

        product = (
                first_order_item.get("product", {})
                or {}
        )

        product_key = product.get("productKey")
        product_name = product.get("name")
        quantity = first_order_item.get("quantity")

        # =====================================
        # 2. Webhook History 저장
        # =====================================

        history = WebhookLogHistory(
            eventType=event_type,
            order_id=order_id,
            payment_key=payment_key,
            product_key=product_key,
            product_name=product_name,
            ticketuser_id=ticket_user_id,
            enrollmentid=payment_id,
            status=status,

            amount=(
                str(amount)
                if amount is not None
                else None
            ),
            method=method,
            name=customer_name,
            approved_at=approved_at,
            created_at=created_at,
            payload=payload_json,
            datetime=now_kst,
        )

        db.add(history)
        db.commit()
        # =====================================
        # 3. 필수값 검증
        # =====================================

        if not order_id:

            raise HTTPException(
                status_code=200,
                detail="Missing orderId",
            )

        # =====================================
        # 4. 중복 Webhook 확인
        # =====================================

        exists = (
            db.query(WebhookLog)
            .filter(
                WebhookLog.order_id == order_id,
                WebhookLog.payment_key == payment_key,
                WebhookLog.status == status,
            )
            .first()
        )


        if exists:

            return {
                "ok": True,
                "message": "duplicate ignored",
                "eventType": event_type,
                "status": status,
                "orderId": order_id,
                "paymentKey": payment_key,
                "paymentId": payment_id,
            }



        # =====================================
        # 5. Webhook Log 생성
        # =====================================

        saved = WebhookLog(
            order_id=order_id,
            payment_key=payment_key,
            ticketuser_id=ticket_user_id,
            enrollmentid=payment_id,
            status=status,
            amount=(
                str(amount)
                if amount is not None
                else None
            ),
            method=method,
            name=customer_name,
            approved_at=approved_at,
            created_at=created_at,
            receipt=receipt_url,
            payload=payload_json,
            datetime=now_kst,
        )


        db.add(saved)
        # =====================================
        # 6. Payment 조회
        # =====================================

        if not payment_id:
            saved.status = "PAYMENT_ID_MISSING"
            db.commit()
            db.refresh(saved)
            return {
                "ok": True,
                "id": saved.id,
                "eventType": event_type,
                "status": status,
                "orderId": order_id,
                "paymentKey": payment_key,
                "message":
                    "payment metadata missing"

            }

        payment_db, is_legacy_fallback = (
            find_payment_by_metadata(
                db=db,
                payment_id=payment_id,
                enrollment_id=None,
            )
        )
        if not payment_db:
            saved.status = (
                "PAYMENT_NOT_FOUND"
            )

            db.commit()
            db.refresh(saved)
            return {
                "ok": True,
                "id": saved.id,
                "eventType": event_type,
                "status": status,
                "orderId": order_id,
                "paymentKey": payment_key,
                "paymentId": payment_id,
                "message":
                    "payment not found"

            }

        # =====================================
        # 7. DONE 처리
        # =====================================

        if status == "DONE":
            before_status = payment_db.status
            # 이미 결제 완료된 경우
            if before_status == Payment.STATUS_PAID:
                if payment_db.toss_payment_key == payment_key:
                    db.commit()
                    db.refresh(saved)
                    return {

                        "ok": True,
                        "id": saved.id,
                        "message":
                            "duplicate DONE webhook ignored",
                        "eventType": event_type,
                        "status": status,
                        "paymentId":
                            payment_db.id,
                        "paymentKey":
                            payment_key,

                    }
                saved.status = (
                    "DUPLICATE_PAYMENT"
                )
                db.commit()
                db.refresh(saved)
                return {

                    "ok": True,
                    "id": saved.id,
                    "message":"duplicate payment detected",
                    "eventType": event_type,
                    "status": status,
                    "paymentId":payment_db.id,
                    "oldPaymentKey":payment_db.toss_payment_key,
                    "newPaymentKey":payment_key,

                }



            # 종료된 Payment에 DONE webhook
            if before_status in {

                Payment.STATUS_FAILED,

            }:
                saved.status = (
                    "CLOSED_PAYMENT_DONE"
                )


                db.commit()
                db.refresh(saved)
                return {
                    "ok": True,
                    "id": saved.id,
                    "message":"closed payment received DONE",
                    "eventType": event_type,
                    "status": status,
                    "paymentId":payment_db.id,
                    "currentPaymentStatus":before_status,
                    "paymentKey":payment_key,

                }
            after_status = (
                Payment.STATUS_PAID
            )
            add_payment_history(
                db=db,
                payment_db=payment_db,
                before_status=before_status,
                after_status=after_status,
                reason="Payment completed",
                payload=payload,
                now_kst=now_kst,
            )
            payment_db.status = after_status
            payment_db.paid_at = now_kst
            apply_common_payment_fields(
                payment_db=payment_db,
                paid_amount=amount,
                toss_payment_key=payment_key,
                order_id=order_id,
                raw_payload=payload_json,
            )

        else:
            saved.status = (
                f"UNHANDLED_{status}"
            )

            if payment_db:
                before_status = payment_db.status
                after_status = 4

                add_payment_history(
                    db=db,
                    payment_db=payment_db,
                    before_status=before_status,
                    after_status=after_status,
                    reason=f"Unhandled Toss status: {status}",
                    payload=payload,
                    now_kst=now_kst,
                )
                payment_db.status = after_status
            db.commit()
            db.refresh(saved)
            return {

                "ok": True,
                "id": saved.id,
                "eventType":event_type,
                "status":status,
                "orderId":order_id,
                "paymentKey":payment_key,
                "paymentId":payment_id,
                "message":"unhandled status",

            }
        # =====================================
        # 9. 최종 저장
        # =====================================

        db.commit()
        db.refresh(saved)

        await manager.send_payment_update(
                payment_id=payment_id ,
                data={
                    "type": "PAYMENT_STATUS_CHANGED",
                    "paymentId": payment_db.id,
                    "status": payment_db.status,
                    "orderId": order_id,
                    "paymentKey": payment_key,
                    "paidAt": (
                        payment_db.paid_at.isoformat()
                        if payment_db.paid_at
                        else None
                    ),
                }
            )



        return {

            "ok": True,
            "id": saved.id,
            "eventType": event_type,
            "status":status,
            "orderId":order_id,
            "paymentKey":payment_key,
            "paymentId":payment_db.id,
            "legacyFallback":is_legacy_fallback,

        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            "Webhook Error:",
            str(e)
        )

        db.rollback()
        try:

            error_history = WebhookLogHistory(
                eventType=event_type,
                order_id=order_id,
                payment_key=payment_key,
                product_key=product_key,
                product_name=product_name,
                ticketuser_id=ticket_user_id,
                enrollmentid=payment_id,
                status="ERROR",
                name=customer_name,
                payload=json.dumps(
                    {
                        "error": str(e),
                        "payload": payload,
                        "paymentId": payment_id,

                    },
                    ensure_ascii=False,
                ),
                datetime=datetime.now(KST),

            )
            db.add(error_history)
            db.commit()



        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Internal server error",

        )

#
# # api/webhook.py
#
# import json
# import os
# from datetime import datetime
# from zoneinfo import ZoneInfo
#
# from fastapi import APIRouter, HTTPException, Request
#
# from app.api.deps import DbSession
# from app.db.models import (
#     Payment,
#     WebhookLog,
#     WebhookLogHistory,
# )
# from app.services.websocket_manager import manager
# from app.services.webhook_service import (
#     add_payment_history,
#     apply_common_payment_fields,
#     find_payment_by_metadata,
#     to_int_or_none,
# )
#
#
# router = APIRouter()
#
# KST = ZoneInfo("Asia/Seoul")
# TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")
#
#
# @router.post(
#     "/webhook/toss",
#     summary="Toss Webhook",
#     tags=["USER API"],
# )
# async def toss_webhook(
#         request: Request,
#         db: DbSession,
# ):
#     payload = None
#
#     event_type = None
#     order_id = None
#     payment_key = None
#     status = None
#     method = None
#     amount = None
#     approved_at = None
#     created_at = None
#     receipt_url = None
#
#     payment_id = None
#     ticket_user_id = None
#     customer_name = None
#
#     product_key = None
#     product_name = None
#     quantity = None
#
#     try:
#         print(
#             "========== Toss Webhook Received =========="
#         )
#
#         payload = await request.json()
#
#         # =====================================
#         # 1. 공통 데이터 파싱
#         # =====================================
#
#         event_type = payload.get(
#             "eventType"
#         )
#
#         data = (
#                 payload.get("data", {})
#                 or {}
#         )
#
#         meta_fields = {}
#         order_items = []
#
#         # =====================================
#         # 1-1. 결제 상태 변경 이벤트
#         #
#         # data 자체가 Payment 객체임.
#         # EXPIRED, ABORTED 등의 결제 시도 상태가
#         # 이 이벤트로 들어온다.
#         # =====================================
#
#         if (
#                 event_type
#                 == "PAYMENT_STATUS_CHANGED"
#         ):
#             payment_data = data
#
#             order_id = payment_data.get(
#                 "orderId"
#             )
#
#             payment_key = payment_data.get(
#                 "paymentKey"
#             )
#
#             status = payment_data.get(
#                 "status"
#             )
#
#             method = payment_data.get(
#                 "method"
#             )
#
#             amount = payment_data.get(
#                 "totalAmount"
#             )
#
#             approved_at = payment_data.get(
#                 "approvedAt"
#             )
#
#             created_at = (
#                     payment_data.get(
#                         "requestedAt"
#                     )
#                     or payload.get(
#                 "createdAt"
#             )
#             )
#
#             receipt_url = (
#                     payment_data.get(
#                         "receipt",
#                         {},
#                     )
#                     or {}
#             ).get("url")
#
#             # PAYMENT_STATUS_CHANGED에는
#             # 일반 티켓 paymentId가 보통 없고
#             # metadata 구조도 ORDER 이벤트와 다를 수 있다.
#             meta_fields = (
#                     payment_data.get(
#                         "metadata",
#                         {},
#                     )
#                     or {}
#             )
#
#             customer_name = None
#             order_items = []
#
#         # =====================================
#         # 1-2. 주문 결제 상태 변경 이벤트
#         #
#         # 내부 Payment 처리, 관리자 거래 목록,
#         # 매출 통계의 기준 이벤트임.
#         # =====================================
#
#         elif (
#                 event_type
#                 == "ORDER_PAYMENT_STATUS_CHANGED"
#         ):
#             payment_data = (
#                     data.get("payment", {})
#                     or {}
#             )
#
#             order_id = (
#                     payment_data.get(
#                         "orderId"
#                     )
#                     or data.get(
#                 "orderKey"
#             )
#             )
#
#             payment_key = (
#                 payment_data.get(
#                     "paymentKey"
#                 )
#             )
#
#             status = payment_data.get(
#                 "status"
#             )
#
#             method = payment_data.get(
#                 "method"
#             )
#
#             amount = (
#                     data.get("amount")
#                     or payment_data.get(
#                 "totalAmount"
#             )
#             )
#
#             approved_at = (
#                 payment_data.get(
#                     "approvedAt"
#                 )
#             )
#
#             created_at = (
#                     data.get("createdAt")
#                     or payment_data.get(
#                 "requestedAt"
#             )
#             )
#
#             receipt_url = (
#                     payment_data.get(
#                         "receipt",
#                         {},
#                     )
#                     or {}
#             ).get("url")
#
#             meta_fields = (
#                     data.get(
#                         "metaFields",
#                         {},
#                     )
#                     or {}
#             )
#
#             customer_name = data.get(
#                 "customerName"
#             )
#
#             order_items = (
#                     data.get(
#                         "orderItems",
#                         [],
#                     )
#                     or []
#             )
#
#         # =====================================
#         # 1-3. 그 외 Toss 이벤트
#         #
#         # 가능한 값은 최대한 파싱해서
#         # History에는 남긴다.
#         # 내부 Payment 처리는 하지 않는다.
#         # =====================================
#
#         else:
#             payment_data = (
#                     data.get("payment", {})
#                     or {}
#             )
#
#             order_id = (
#                     payment_data.get(
#                         "orderId"
#                     )
#                     or data.get(
#                 "orderId"
#             )
#                     or data.get(
#                 "orderKey"
#             )
#             )
#
#             payment_key = (
#                     payment_data.get(
#                         "paymentKey"
#                     )
#                     or data.get(
#                 "paymentKey"
#             )
#             )
#
#             status = (
#                     payment_data.get(
#                         "status"
#                     )
#                     or data.get(
#                 "status"
#             )
#             )
#
#             method = (
#                     payment_data.get(
#                         "method"
#                     )
#                     or data.get(
#                 "method"
#             )
#             )
#
#             amount = (
#                     data.get("amount")
#                     or payment_data.get(
#                 "totalAmount"
#             )
#                     or data.get(
#                 "totalAmount"
#             )
#             )
#
#             approved_at = (
#                     payment_data.get(
#                         "approvedAt"
#                     )
#                     or data.get(
#                 "approvedAt"
#             )
#             )
#
#             created_at = (
#                     data.get(
#                         "createdAt"
#                     )
#                     or payment_data.get(
#                 "requestedAt"
#             )
#                     or data.get(
#                 "requestedAt"
#             )
#                     or payload.get(
#                 "createdAt"
#             )
#             )
#
#             receipt_url = (
#                     payment_data.get(
#                         "receipt",
#                         {},
#                     )
#                     or data.get(
#                 "receipt",
#                 {},
#             )
#                     or {}
#             ).get("url")
#
#             meta_fields = (
#                     data.get(
#                         "metaFields",
#                         {},
#                     )
#                     or data.get(
#                 "metadata",
#                 {},
#             )
#                     or payment_data.get(
#                 "metadata",
#                 {},
#             )
#                     or {}
#             )
#
#             customer_name = data.get(
#                 "customerName"
#             )
#
#             order_items = (
#                     data.get(
#                         "orderItems",
#                         [],
#                     )
#                     or []
#             )
#
#         # =====================================
#         # 1-4. 내부 메타데이터 파싱
#         # =====================================
#
#         payment_id = to_int_or_none(
#             meta_fields.get(
#                 "paymentId"
#             )
#         )
#
#         ticket_user_id = to_int_or_none(
#             meta_fields.get(
#                 "ticketUserId"
#             )
#         )
#
#         # =====================================
#         # 1-5. 상품 정보 파싱
#         # =====================================
#
#         first_order_item = (
#             order_items[0]
#             if order_items
#             else {}
#         )
#
#         product = (
#                 first_order_item.get(
#                     "product",
#                     {},
#                 )
#                 or {}
#         )
#
#         product_key = product.get(
#             "productKey"
#         )
#
#         product_name = product.get(
#             "name"
#         )
#
#         quantity = first_order_item.get(
#             "quantity"
#         )
#
#         now_kst = datetime.now(KST)
#
#         payload_json = json.dumps(
#             payload,
#             ensure_ascii=False,
#         )
#
#         # =====================================
#         # 2. 모든 웹훅 History 저장
#         # =====================================
#
#         history = WebhookLogHistory(
#             eventType=event_type,
#             order_id=order_id,
#             payment_key=payment_key,
#             product_key=product_key,
#             product_name=product_name,
#             ticketuser_id=ticket_user_id,
#             enrollmentid=payment_id,
#             status=status,
#             amount=(
#                 str(amount)
#                 if amount is not None
#                 else None
#             ),
#             method=method,
#             name=customer_name,
#             approved_at=approved_at,
#             created_at=created_at,
#             payload=payload_json,
#             datetime=now_kst,
#         )
#
#         db.add(history)
#         db.commit()
#
#         # =====================================
#         # 3. PAYMENT_STATUS_CHANGED
#         #
#         # EXPIRED, ABORTED, DONE 등의 상태를
#         # History에는 정확히 저장하지만
#         # 내부 Payment 변경은 하지 않는다.
#         # =====================================
#
#         if (
#                 event_type
#                 == "PAYMENT_STATUS_CHANGED"
#         ):
#             return {
#                 "ok": True,
#                 "message": (
#                     "payment status history saved"
#                 ),
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#             }
#
#         # =====================================
#         # 4. 지원하지 않는 이벤트
#         #
#         # History만 저장하고 종료한다.
#         # =====================================
#
#         if (
#                 event_type
#                 != "ORDER_PAYMENT_STATUS_CHANGED"
#         ):
#             return {
#                 "ok": True,
#                 "message": (
#                     "unsupported event history saved"
#                 ),
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#             }
#
#         # 여기부터는
#         # ORDER_PAYMENT_STATUS_CHANGED만 통과함.
#
#         # =====================================
#         # 5. 필수값 검증
#         # =====================================
#
#         if not order_id:
#             return {
#                 "ok": True,
#                 "message": "missing orderId",
#                 "eventType": event_type,
#                 "status": status,
#                 "paymentKey": payment_key,
#             }
#
#         if not payment_key:
#             return {
#                 "ok": True,
#                 "message": "missing paymentKey",
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#             }
#
#         # =====================================
#         # 6. 중복 ORDER Webhook 확인
#         # =====================================
#
#         exists = (
#             db.query(WebhookLog)
#             .filter(
#                 WebhookLog.order_id
#                 == order_id,
#                 WebhookLog.payment_key
#                 == payment_key,
#                 WebhookLog.status
#                 == status,
#                 )
#             .first()
#         )
#
#         if exists:
#             return {
#                 "ok": True,
#                 "message": (
#                     "duplicate ignored"
#                 ),
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#                 "paymentId": payment_id,
#             }
#
#         # =====================================
#         # 7. 대표 Webhook Log 생성
#         # =====================================
#
#         saved = WebhookLog(
#             order_id=order_id,
#             payment_key=payment_key,
#             product_key=product_key,
#             product_name=product_name,
#             ticketuser_id=ticket_user_id,
#             enrollmentid=payment_id,
#             status=status,
#             amount=(
#                 str(amount)
#                 if amount is not None
#                 else None
#             ),
#             method=method,
#             name=customer_name,
#             approved_at=approved_at,
#             created_at=created_at,
#             receipt=receipt_url,
#             payload=payload_json,
#             datetime=now_kst,
#         )
#
#         db.add(saved)
#
#         # =====================================
#         # 8. Payment ID 없는 외부 결제
#         #
#         # 스폰서 LinkPay 등의 외부 상품은
#         # 내부 Payment ID가 없는 것이 정상임.
#         #
#         # WebhookLog는 저장하되
#         # 내부 Payment 처리는 하지 않는다.
#         # =====================================
#
#         if not payment_id:
#             saved.status = (
#                 "PAYMENT_ID_MISSING"
#             )
#
#             db.commit()
#             db.refresh(saved)
#
#             return {
#                 "ok": True,
#                 "id": saved.id,
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#                 "message": (
#                     "payment metadata missing"
#                 ),
#             }
#
#         # =====================================
#         # 9. 내부 Payment 조회
#         # =====================================
#
#         payment_db, is_legacy_fallback = (
#             find_payment_by_metadata(
#                 db=db,
#                 payment_id=payment_id,
#                 enrollment_id=None,
#             )
#         )
#
#         if not payment_db:
#             saved.status = (
#                 "PAYMENT_NOT_FOUND"
#             )
#
#             db.commit()
#             db.refresh(saved)
#
#             return {
#                 "ok": True,
#                 "id": saved.id,
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#                 "paymentId": payment_id,
#                 "message": (
#                     "payment not found"
#                 ),
#             }
#
#         # =====================================
#         # 10. DONE 처리
#         # =====================================
#
#         if status == "DONE":
#             before_status = (
#                 payment_db.status
#             )
#
#             # 이미 동일 paymentKey로 결제 완료
#             if (
#                     before_status
#                     == Payment.STATUS_PAID
#             ):
#                 if (
#                         payment_db.toss_payment_key
#                         == payment_key
#                 ):
#                     db.commit()
#                     db.refresh(saved)
#
#                     return {
#                         "ok": True,
#                         "id": saved.id,
#                         "message": (
#                             "duplicate DONE webhook ignored"
#                         ),
#                         "eventType": event_type,
#                         "status": status,
#                         "paymentId": (
#                             payment_db.id
#                         ),
#                         "paymentKey": (
#                             payment_key
#                         ),
#                     }
#
#                 # 같은 내부 Payment에
#                 # 다른 paymentKey의 DONE 발생
#                 saved.status = (
#                     "DUPLICATE_PAYMENT"
#                 )
#
#                 db.commit()
#                 db.refresh(saved)
#
#                 return {
#                     "ok": True,
#                     "id": saved.id,
#                     "message": (
#                         "duplicate payment detected"
#                     ),
#                     "eventType": event_type,
#                     "status": status,
#                     "paymentId": (
#                         payment_db.id
#                     ),
#                     "oldPaymentKey": (
#                         payment_db.toss_payment_key
#                     ),
#                     "newPaymentKey": (
#                         payment_key
#                     ),
#                 }
#
#             # 실패로 종료된 Payment에
#             # 뒤늦게 DONE이 들어온 경우
#             if before_status in {
#                 Payment.STATUS_FAILED,
#             }:
#                 saved.status = (
#                     "CLOSED_PAYMENT_DONE"
#                 )
#
#                 db.commit()
#                 db.refresh(saved)
#
#                 return {
#                     "ok": True,
#                     "id": saved.id,
#                     "message": (
#                         "closed payment received DONE"
#                     ),
#                     "eventType": event_type,
#                     "status": status,
#                     "paymentId": (
#                         payment_db.id
#                     ),
#                     "currentPaymentStatus": (
#                         before_status
#                     ),
#                     "paymentKey": (
#                         payment_key
#                     ),
#                 }
#
#             after_status = (
#                 Payment.STATUS_PAID
#             )
#
#             add_payment_history(
#                 db=db,
#                 payment_db=payment_db,
#                 before_status=before_status,
#                 after_status=after_status,
#                 reason="Payment completed",
#                 payload=payload,
#                 now_kst=now_kst,
#             )
#
#             payment_db.status = (
#                 after_status
#             )
#
#             payment_db.paid_at = (
#                 now_kst
#             )
#
#             apply_common_payment_fields(
#                 payment_db=payment_db,
#                 paid_amount=amount,
#                 toss_payment_key=payment_key,
#                 order_id=order_id,
#                 raw_payload=payload_json,
#             )
#
#         # =====================================
#         # 11. DONE 외 상태 처리
#         # =====================================
#
#         else:
#             saved.status = (
#                 f"UNHANDLED_{status}"
#             )
#
#             before_status = (
#                 payment_db.status
#             )
#
#             after_status = (
#                 Payment.STATUS_FAILED
#             )
#
#             add_payment_history(
#                 db=db,
#                 payment_db=payment_db,
#                 before_status=before_status,
#                 after_status=after_status,
#                 reason=(
#                     f"Unhandled Toss status: "
#                     f"{status}"
#                 ),
#                 payload=payload,
#                 now_kst=now_kst,
#             )
#
#             payment_db.status = (
#                 after_status
#             )
#
#             db.commit()
#             db.refresh(saved)
#
#             return {
#                 "ok": True,
#                 "id": saved.id,
#                 "eventType": event_type,
#                 "status": status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#                 "paymentId": payment_id,
#                 "message": (
#                     "unhandled status"
#                 ),
#             }
#
#         # =====================================
#         # 12. 최종 저장
#         # =====================================
#
#         db.commit()
#         db.refresh(saved)
#
#         # =====================================
#         # 13. WebSocket 상태 전송
#         # =====================================
#
#         await manager.send_payment_update(
#             payment_id=payment_id,
#             data={
#                 "type": (
#                     "PAYMENT_STATUS_CHANGED"
#                 ),
#                 "paymentId": payment_db.id,
#                 "status": payment_db.status,
#                 "orderId": order_id,
#                 "paymentKey": payment_key,
#                 "paidAt": (
#                     payment_db.paid_at.isoformat()
#                     if payment_db.paid_at
#                     else None
#                 ),
#             },
#         )
#
#         return {
#             "ok": True,
#             "id": saved.id,
#             "eventType": event_type,
#             "status": status,
#             "orderId": order_id,
#             "paymentKey": payment_key,
#             "paymentId": payment_db.id,
#             "legacyFallback": (
#                 is_legacy_fallback
#             ),
#         }
#
#     except HTTPException:
#         raise
#
#     except Exception as exc:
#         print(
#             "Webhook Error:",
#             str(exc),
#         )
#
#         db.rollback()
#
#         try:
#             error_history = (
#                 WebhookLogHistory(
#                     eventType=event_type,
#                     order_id=order_id,
#                     payment_key=payment_key,
#                     product_key=product_key,
#                     product_name=product_name,
#                     ticketuser_id=(
#                         ticket_user_id
#                     ),
#                     enrollmentid=payment_id,
#                     status="ERROR",
#                     amount=(
#                         str(amount)
#                         if amount is not None
#                         else None
#                     ),
#                     method=method,
#                     name=customer_name,
#                     approved_at=approved_at,
#                     created_at=created_at,
#                     payload=json.dumps(
#                         {
#                             "error": str(exc),
#                             "payload": payload,
#                             "paymentId": (
#                                 payment_id
#                             ),
#                         },
#                         ensure_ascii=False,
#                     ),
#                     datetime=datetime.now(
#                         KST
#                     ),
#                 )
#             )
#
#             db.add(error_history)
#             db.commit()
#
#         except Exception:
#             db.rollback()
#
#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "Internal server error"
#             ),
#         ) from exc