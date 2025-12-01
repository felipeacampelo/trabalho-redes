"""
Manipulador de conexão peer-to-peer
"""
import socket
import json
import logging
import threading
import uuid
from typing import Optional, Callable
from datetime import datetime
from models import Message, MessageType

logger = logging.getLogger(__name__)


class PeerConnection:
    """Gerencia uma única conexão TCP peer-to-peer"""
    
    def __init__(self, peer_id: str, sock: socket.socket, direction: str, 
                 on_message: Callable[[str, Message], None],
                 on_disconnect: Callable[[str], None]):
        self.peer_id = peer_id
        self.sock = sock
        self.direction = direction  # "inbound" (entrada) ou "outbound" (saída)
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.running = False
        self.recv_thread = None
        self.max_line_size = 32768
        self.send_lock = threading.Lock()
    
    def start(self):
        """Inicia recebimento de mensagens"""
        self.running = True
        self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.recv_thread.start()
    
    def stop(self):
        """Para a conexão"""
        self.running = False
        try:
            self.sock.close()
        except:
            pass
    
    def send_message(self, message: Message) -> bool:
        """Envia uma mensagem para o peer"""
        try:
            with self.send_lock:
                msg_json = json.dumps(message.to_dict()) + "\n"
                msg_bytes = msg_json.encode('utf-8')
                
                if len(msg_bytes) > self.max_line_size:
                    logger.error(f"Message too large: {len(msg_bytes)} bytes")
                    return False
                
                self.sock.sendall(msg_bytes)
                logger.debug(f"Sent {message.msg_type.value} to {self.peer_id}")
                return True
        except Exception as e:
            logger.error(f"Error sending message to {self.peer_id}: {e}")
            return False
    
    def _receive_loop(self):
        """Recebe mensagens do peer"""
        buffer = b""
        
        try:
            while self.running:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        logger.info(f"Connection closed by {self.peer_id}")
                        break
                    
                    buffer += chunk
                    
                    # Processa linhas completas
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        
                        if len(line) > self.max_line_size:
                            logger.error(f"Line too long from {self.peer_id}")
                            continue
                        
                        try:
                            line_str = line.decode('utf-8').strip()
                            if line_str:
                                msg_dict = json.loads(line_str)
                                message = Message.from_dict(msg_dict)
                                logger.debug(f"Received {message.msg_type.value} from {self.peer_id}")
                                self.on_message(self.peer_id, message)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON from {self.peer_id}: {e}")
                        except Exception as e:
                            logger.error(f"Error processing message from {self.peer_id}: {e}")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error in receive loop for {self.peer_id}: {e}")
                    break
        
        finally:
            self.running = False
            self.on_disconnect(self.peer_id)


class PeerServer:
    """Escuta conexões de entrada de peers"""
    
    def __init__(self, port: int, peer_id: str,
                 on_connection: Callable[[str, socket.socket], None]):
        self.port = port
        self.peer_id = peer_id
        self.on_connection = on_connection
        self.server_sock = None
        self.running = False
        self.accept_thread = None
    
    def start(self):
        """Inicia escuta de conexões"""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(('0.0.0.0', self.port))
            self.server_sock.listen(10)
            self.server_sock.settimeout(1)
            
            self.running = True
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            
            logger.info(f"[PeerServer] Listening on port {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start peer server: {e}")
            return False
    
    def stop(self):
        """Para o servidor"""
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass
    
    def _accept_loop(self):
        """Aceita conexões de entrada"""
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
                logger.info(f"[PeerServer] Incoming connection from {addr}")
                
                # Trata em thread separada
                threading.Thread(
                    target=self._handle_inbound,
                    args=(client_sock, addr),
                    daemon=True
                ).start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def _handle_inbound(self, sock: socket.socket, addr):
        """Trata handshake de conexão de entrada"""
        try:
            sock.settimeout(10)
            
            # Aguarda HELLO
            data = b""
            while b'\n' not in data:
                chunk = sock.recv(4096)
                if not chunk:
                    logger.warning(f"Connection closed before HELLO from {addr}")
                    sock.close()
                    return
                data += chunk
            
            line, _ = data.split(b'\n', 1)
            hello_dict = json.loads(line.decode('utf-8'))
            hello_msg = Message.from_dict(hello_dict)
            
            if hello_msg.msg_type != MessageType.HELLO:
                logger.warning(f"Expected HELLO, got {hello_msg.msg_type.value} from {addr}")
                sock.close()
                return
            
            remote_peer_id = hello_msg.src
            logger.info(f"[PeerServer] HELLO from {remote_peer_id}")
            
            # Envia HELLO_OK
            hello_ok = Message(
                msg_type=MessageType.HELLO_OK,
                msg_id=str(uuid.uuid4()),
                src=self.peer_id,
                version="1.0",
                features=["ack", "metrics"]
            )
            
            hello_ok_json = json.dumps(hello_ok.to_dict()) + "\n"
            sock.sendall(hello_ok_json.encode('utf-8'))
            
            logger.info(f"[PeerServer] Inbound connected: {remote_peer_id}")
            
            # Notifica o pai
            self.on_connection(remote_peer_id, sock)
            
        except Exception as e:
            logger.error(f"Error handling inbound connection from {addr}: {e}")
            try:
                sock.close()
            except:
                pass
