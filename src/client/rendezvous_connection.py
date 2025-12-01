"""
Manipulador de conexão com o servidor Rendezvous
"""
import socket
import json
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class RendezvousConnection:
    """Gerencia comunicação com o servidor Rendezvous"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.max_line_size = 32768
    
    def _send_command(self, command: dict) -> Optional[dict]:
        """Envia um comando para o servidor Rendezvous e obtém resposta"""
        try:
            # Cria nova conexão para cada comando
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.host, self.port))
            
            # Envia comando
            command_json = json.dumps(command) + "\n"
            sock.sendall(command_json.encode('utf-8'))
            
            # Recebe resposta
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b'\n' in response_data:
                    break
            
            sock.close()
            
            # Processa resposta
            response_str = response_data.decode('utf-8').strip()
            if response_str:
                return json.loads(response_str)
            
            return None
            
        except socket.timeout:
            logger.error(f"Timeout connecting to Rendezvous server at {self.host}:{self.port}")
            return None
        except ConnectionRefusedError:
            logger.error(f"Connection refused by Rendezvous server at {self.host}:{self.port}")
            return None
        except Exception as e:
            logger.error(f"Error communicating with Rendezvous: {e}")
            return None
    
    def register(self, namespace: str, name: str, port: int, ttl: int = 7200) -> Optional[dict]:
        """Registra peer no servidor Rendezvous"""
        command = {
            "type": "REGISTER",
            "namespace": namespace,
            "name": name,
            "port": port,
            "ttl": ttl
        }
        
        logger.info(f"Registering {name}@{namespace} on port {port} with TTL {ttl}s")
        response = self._send_command(command)
        
        if response and response.get("status") == "OK":
            logger.info(f"Successfully registered: {response}")
            return response
        else:
            logger.error(f"Registration failed: {response}")
            return None
    
    def discover(self, namespace: Optional[str] = None) -> List[Dict]:
        """Descobre peers em um namespace (ou todos se namespace for None)"""
        command = {"type": "DISCOVER"}
        if namespace:
            command["namespace"] = namespace
        
        logger.debug(f"Discovering peers in namespace: {namespace or 'all'}")
        response = self._send_command(command)
        
        if response and response.get("status") == "OK":
            peers = response.get("peers", [])
            logger.debug(f"Discovered {len(peers)} peers")
            return peers
        else:
            logger.warning(f"Discovery failed: {response}")
            return []
    
    def unregister(self, namespace: str, name: str, port: int) -> bool:
        """Remove registro do peer no servidor Rendezvous"""
        command = {
            "type": "UNREGISTER",
            "namespace": namespace,
            "name": name,
            "port": port
        }
        
        logger.info(f"Unregistering {name}@{namespace}")
        response = self._send_command(command)
        
        if response and response.get("status") == "OK":
            logger.info("Successfully unregistered")
            return True
        else:
            logger.error(f"Unregister failed: {response}")
            return False
