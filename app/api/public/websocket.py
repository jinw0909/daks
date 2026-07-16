print("========== websocket.py loaded ==========")

import asyncio

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect
)

from app.services.websocket_manager import manager

from app.db.session import SessionLocal
from app.db.models import Payment


router = APIRouter()



@router.websocket(
    "/ws/payment/{payment_id}"
)
async def payment_socket(
    websocket: WebSocket,
    payment_id: int
):

    await manager.connect(
        payment_id,
        websocket
    )


    print(
        f"[WS CONNECT] payment_id={payment_id}"
    )


    # ==================================
    # 재접속 시 현재 결제 상태 전달
    # ==================================

    db = SessionLocal()

    try:

        payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id
            )
            .first()
        )


        if payment:

            await websocket.send_json(
                {
                    "type": "PAYMENT_STATUS",
                    "paymentId": payment.id,
                    "status": payment.status,
                    "paidAt": (
                        payment.paid_at.isoformat()
                        if payment.paid_at
                        else None
                    )
                }
            )


    finally:

        db.close()



    try:

        while True:

            try:

                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30
                )


                if message == "ping":

                    await websocket.send_text(
                        "pong"
                    )


            except asyncio.TimeoutError:

                await websocket.send_json(
                    {
                        "type": "ping"
                    }
                )


    except WebSocketDisconnect:

        print(
            f"[WS DISCONNECT] payment_id={payment_id}"
        )


    except Exception as e:

        print(
            f"[WS ERROR] {e}"
        )


    finally:

        manager.disconnect(
            payment_id,
            websocket
        )