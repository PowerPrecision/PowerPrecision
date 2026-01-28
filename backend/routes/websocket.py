"""
====================================================================
ROTAS WEBSOCKET - CREDITOIMO
====================================================================
Endpoints WebSocket para comunicação em tempo real.
====================================================================
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from config import JWT_SECRET, JWT_ALGORITHM
from database import db
from services.websocket_manager import manager, WSEventType, create_ws_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def verify_websocket_token(token: str) -> dict:
    """Verificar token JWT para conexão WebSocket."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        # Verificar se o utilizador existe
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        
        if not user or user.get("is_active") == False:
            return None
        
        return user
    except JWTError as e:
        logger.error(f"Erro JWT WebSocket: {e}")
        return None


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    Endpoint WebSocket para notificações em tempo real.
    
    Uso no frontend:
    ```javascript
    const ws = new WebSocket(`wss://domain.com/api/ws/notifications?token=${accessToken}`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Notificação:', data);
    };
    ```
    """
    # Verificar autenticação
    user = await verify_websocket_token(token)
    
    if not user:
        await websocket.close(code=4001, reason="Token inválido ou expirado")
        return
    
    user_id = user["id"]
    
    try:
        # Conectar
        await manager.connect(websocket, user_id)
        
        # Enviar confirmação de conexão
        await websocket.send_json(create_ws_message(
            WSEventType.CONNECTION_STATUS,
            {
                "status": "connected",
                "user_id": user_id,
                "user_name": user.get("name", ""),
                "connected_users": len(manager.get_connected_users())
            }
        ))
        
        # Notificar outros utilizadores (opcional - apenas admins/ceos)
        if user.get("role") in ["admin", "ceo"]:
            await manager.broadcast(
                create_ws_message(
                    WSEventType.USER_ONLINE,
                    {"user_id": user_id, "user_name": user.get("name", "")}
                ),
                exclude_user=user_id
            )
        
        # Loop para receber mensagens
        while True:
            try:
                data = await websocket.receive_json()
                
                # Processar diferentes tipos de mensagens do cliente
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    # Responder ao ping com pong (heartbeat)
                    await websocket.send_json(create_ws_message(
                        WSEventType.HEARTBEAT,
                        {"status": "pong"}
                    ))
                
                elif msg_type == "mark_notification_read":
                    # Marcar notificação como lida via WebSocket
                    notification_id = data.get("notification_id")
                    if notification_id:
                        await db.notifications.update_one(
                            {"id": notification_id, "user_id": user_id},
                            {"$set": {"read": True}}
                        )
                        await websocket.send_json(create_ws_message(
                            WSEventType.NOTIFICATION_READ,
                            {"notification_id": notification_id}
                        ))
                
                elif msg_type == "mark_all_read":
                    # Marcar todas as notificações como lidas
                    await db.notifications.update_many(
                        {"user_id": user_id, "read": False},
                        {"$set": {"read": True}}
                    )
                    await websocket.send_json(create_ws_message(
                        WSEventType.ALL_NOTIFICATIONS_READ,
                        {"status": "success"}
                    ))
                
            except Exception as e:
                logger.error(f"Erro ao processar mensagem WebSocket: {e}")
                # Continuar o loop mesmo com erros de mensagem
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket desconectado: {user_id}")
        
        # Notificar outros utilizadores (opcional)
        if user.get("role") in ["admin", "ceo"]:
            await manager.broadcast(
                create_ws_message(
                    WSEventType.USER_OFFLINE,
                    {"user_id": user_id, "user_name": user.get("name", "")}
                ),
                exclude_user=user_id
            )
    
    except Exception as e:
        logger.error(f"Erro WebSocket: {e}")
        manager.disconnect(websocket)


@router.get("/ws/status")
async def websocket_status():
    """Obter estado das conexões WebSocket."""
    return {
        "total_connections": manager.get_total_connections(),
        "connected_users": len(manager.get_connected_users()),
        "user_ids": manager.get_connected_users()
    }
