from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        # payment_id 기준 연결 관리
        self.connections: Dict[int, List[WebSocket]] = {}


    async def connect(
        self,
        payment_id: int,
        websocket: WebSocket
    ):

        await websocket.accept()

        if payment_id not in self.connections:
            self.connections[payment_id] = []

        self.connections[payment_id].append(websocket)



    def disconnect(
        self,
        payment_id: int,
        websocket: WebSocket
    ):

        if payment_id in self.connections:

            if websocket in self.connections[payment_id]:
                self.connections[payment_id].remove(websocket)


            if not self.connections[payment_id]:
                del self.connections[payment_id]



    async def send_payment_update(
        self,
        payment_id:int,
        data:dict
    ):

        sockets = self.connections.get(
            payment_id,
            []
        )

        dead = []

        for websocket in sockets:

            try:

                await websocket.send_json(data)

            except Exception:

                dead.append(websocket)


        for ws in dead:

            self.disconnect(
                payment_id,
                ws
            )



manager = ConnectionManager()