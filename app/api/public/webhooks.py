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
        # =====================================
        # 2. Webhook History 저장
        # =====================================

        history = WebhookLogHistory(
            eventType=event_type,
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

