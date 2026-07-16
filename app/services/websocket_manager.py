from typing import Dict, List

from fastapi import WebSocket

import asyncio



class ConnectionManager:


    def __init__(self):

        # payment_id 기준 websocket 관리
        self.connections: Dict[int, List[WebSocket]] = {}

        self.lock = asyncio.Lock()



    async def connect(
        self,
        payment_id: int,
        websocket: WebSocket
    ):


        await websocket.accept()


        async with self.lock:


            if payment_id not in self.connections:

                self.connections[payment_id] = []



            if websocket not in self.connections[payment_id]:

                self.connections[payment_id].append(
                    websocket
                )


            count = len(
                self.connections[payment_id]
            )


        print(
            f"[WS CONNECTED] payment_id={payment_id}, count={count}"
        )




    def disconnect(
        self,
        payment_id: int,
        websocket: WebSocket
    ):


        sockets = self.connections.get(
            payment_id
        )


        if not sockets:

            return



        if websocket in sockets:

            sockets.remove(
                websocket
            )



        if len(sockets) == 0:

            del self.connections[payment_id]



        print(
            f"[WS REMOVED] payment_id={payment_id}"
        )




    async def send_payment_update(
        self,
        payment_id: int,
        data: dict
    ):


        # 원본 리스트 복사
        sockets = list(
            self.connections.get(
                payment_id,
                []
            )
        )


        if not sockets:

            print(
                f"[WS NONE] payment_id={payment_id}"
            )

            return



        dead = []



        for websocket in sockets:


            try:

                await websocket.send_json(
                    data
                )


                print(
                    f"[WS SEND] payment_id={payment_id}"
                )


            except Exception as e:


                print(
                    f"[WS SEND FAILED] payment_id={payment_id}, error={e}"
                )


                dead.append(
                    websocket
                )



        # 죽은 연결 제거
        for websocket in dead:


            self.disconnect(
                payment_id,
                websocket
            )




    def get_connection_count(
        self,
        payment_id:int
    ):


        return len(
            self.connections.get(
                payment_id,
                []
            )
        )




manager = ConnectionManager()