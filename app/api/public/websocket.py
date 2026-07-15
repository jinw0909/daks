print("========== websocket.py loaded ==========")
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect
)

from app.services.websocket_manager import manager


router = APIRouter()



@router.websocket(
    "/ws/payment/{payment_id}"
)
async def payment_socket(
    websocket: WebSocket,
    payment_id:int
):

    await manager.connect(
        payment_id,
        websocket
    )


    try:
        
        while True:

            # 클라이언트 연결 유지
            await websocket.receive_text()


    except WebSocketDisconnect:

        manager.disconnect(
            payment_id,
            websocket
        )