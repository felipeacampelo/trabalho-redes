"""
Cliente Principal de Chat P2P
"""
import logging
import socket
import uuid
import threading
import time
from typing import Dict, Optional
from datetime import datetime

from models import PeerInfo, PeerStatus, Message, MessageType, ConnectionInfo
from state import PeerState
from rendezvous_connection import RendezvousConnection
from peer_connection import PeerConnection, PeerServer
from message_router import MessageRouter
from keep_alive import KeepAlive
from peer_table import PeerTable
from cli import CLI

logger = logging.getLogger(__name__)


class P2PClient:
    """Cliente Principal de Chat P2P"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Identidade
        self.namespace = config['peer']['namespace']
        self.name = config['peer']['name']
        self.port = config['peer']['port']
        self.peer_id = f"{self.name}@{self.namespace}"
        
        # Estado
        self.state = PeerState()
        self.connections: Dict[str, PeerConnection] = {}
        self.conn_lock = threading.RLock()
        self.connecting_peers: set = set()  # Rastreia peers em processo de conexão
        
        # Componentes
        self.rendezvous = RendezvousConnection(
            config['rendezvous']['host'],
            config['rendezvous']['port']
        )
        
        self.peer_server = PeerServer(
            self.port,
            self.peer_id,
            self._on_inbound_connection
        )
        
        self.message_router = MessageRouter(
            self.peer_id,
            self._send_message_to_peer,
            self._get_connected_peer_ids,
            self._get_peers_by_namespace,
            config['connection']['ack_timeout']
        )
        
        self.keep_alive = KeepAlive(
            config['connection']['ping_interval'],
            self._send_message_to_peer
        )
        
        self.peer_table = PeerTable(
            config['connection']['max_reconnect_attempts'],
            config['connection']['reconnect_backoff_base'],
            config['connection']['reconnect_backoff_max'],
            self._connect_to_peer
        )
        
        self.cli = CLI(
            on_peers=self._cmd_peers,
            on_msg=self._cmd_msg,
            on_pub=self._cmd_pub,
            on_conn=self._cmd_conn,
            on_rtt=self._cmd_rtt,
            on_reconnect=self._cmd_reconnect,
            on_log=self._cmd_log,
            on_quit=self._cmd_quit,
            on_relay=self._cmd_relay
        )
        
        # Controle
        self.running = False
        self.stop_event = threading.Event()  # Evento para interromper sleeps
        self.discovery_thread = None
        self.ping_thread = None
        self.discovery_interval = config['connection']['discovery_interval']
    
    def start(self):
        """Inicia o cliente P2P"""
        logger.info(f"Starting P2P Client: {self.peer_id}")
        
        # Registra no Rendezvous
        result = self.rendezvous.register(self.namespace, self.name, self.port)
        if not result:
            logger.error("Failed to register with Rendezvous server")
            return False
        
        # Armazena nosso IP público para detecção de peer local
        self.my_public_ip = result.get('ip')
        logger.info(f"Registered with Rendezvous: {result}")
        
        # Inicia servidor de peers
        if not self.peer_server.start():
            logger.error("Failed to start peer server")
            return False
        
        # Inicia componentes
        self.message_router.start()
        self.keep_alive.start()
        self.peer_table.start()
        
        # Inicia descoberta
        self.running = True
        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.discovery_thread.start()
        
        # Inicia ping periódico
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()
        
        # Inicia CLI
        self.cli.start()
        
        logger.info("P2P Client started successfully")
        return True
    
    def stop(self):
        """Para o cliente P2P"""
        logger.info("Stopping P2P Client...")
        
        # Para todas as threads em segundo plano PRIMEIRO
        self.running = False
        self.stop_event.set()  # Sinaliza para threads pararem imediatamente
        self.cli.stop()
        
        # Para todos os componentes que podem interferir no desligamento
        self.peer_table.stop()
        self.keep_alive.stop()
        self.message_router.stop()
        self.peer_server.stop()  # Para de aceitar novas conexões
        
        # Aguarda threads terminarem
        if self.discovery_thread and self.discovery_thread.is_alive():
            self.discovery_thread.join(timeout=2)
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(timeout=2)
        
        # Agora envia BYE para todos os peers conectados
        with self.conn_lock:
            for peer_id in list(self.connections.keys()):
                self._send_bye(peer_id)
        
        # Dá tempo para peers responderem com BYE_OK
        time.sleep(0.5)
        
        # Fecha todas as conexões
        with self.conn_lock:
            for conn in self.connections.values():
                conn.stop()
            self.connections.clear()
        
        # Remove registro do Rendezvous
        self.rendezvous.unregister(self.namespace, self.name, self.port)
        
        logger.info("P2P Client stopped")
    
    def _discovery_loop(self):
        """Descobre peers periodicamente"""
        # Descoberta inicial
        self._discover_peers()
        
        while self.running:
            try:
                # Usa wait() em vez de sleep() para poder ser interrompido
                if self.stop_event.wait(timeout=self.discovery_interval):
                    break  # Evento sinalizado, sair do loop
                if not self.running:
                    break
                self._discover_peers()
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
    
    def _discover_peers(self):
        """Descobre peers do Rendezvous"""
        if not self.running:
            return
            
        logger.info("[Discovery] Discovering peers...")
        peers = self.rendezvous.discover()
        
        if peers and self.running:
            logger.info(f"[Discovery] Found {len(peers)} peers")
            self.peer_table.update_peers(peers, self.peer_id)
            
            # Tenta conectar a peers desconectados (ignora se já está conectando)
            for peer_data in peers:
                peer_id = f"{peer_data['name']}@{peer_data['namespace']}"
                if peer_id != self.peer_id:
                    peer = self.peer_table.get_peer(peer_id)
                    if peer and peer.status == PeerStatus.DISCONNECTED:
                        peer.status = PeerStatus.CONNECTING
                        if not self._connect_to_peer(peer):
                            peer.status = PeerStatus.DISCONNECTED
    
    def _ping_loop(self):
        """Envia PINGs periodicamente"""
        while self.running:
            try:
                # Usa wait() em vez de sleep() para poder ser interrompido
                if self.stop_event.wait(timeout=self.keep_alive.ping_interval):
                    break  # Evento sinalizado, sair do loop
                if not self.running:
                    break
                
                with self.conn_lock:
                    for peer_id in list(self.connections.keys()):
                        self.keep_alive.send_ping(peer_id)
                
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
    
    def _connect_to_peer(self, peer: PeerInfo) -> bool:
        """Estabelece conexão de saída para um peer"""
        with self.conn_lock:
            if peer.peer_id in self.connections:
                logger.debug(f"Already connected to {peer.peer_id}")
                return True
            if peer.peer_id in self.connecting_peers:
                logger.debug(f"Already connecting to {peer.peer_id}")
                return False
            self.connecting_peers.add(peer.peer_id)
        
        try:
            # Detecta se peer está na mesma máquina (mesmo IP público)
            target_ip = peer.ip
            if hasattr(self, 'my_public_ip') and peer.ip == self.my_public_ip:
                target_ip = '127.0.0.1'
                logger.info(f"Detected local peer {peer.peer_id}, using localhost")
            
            logger.info(f"Connecting to {peer.peer_id} at {target_ip}:{peer.port}")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((target_ip, peer.port))
            
            # Envia HELLO
            hello = Message(
                msg_type=MessageType.HELLO,
                msg_id=str(uuid.uuid4()),
                src=self.peer_id,
                version="1.0",
                features=["ack", "metrics"]
            )
            
            hello_json = hello.to_dict()
            import json
            sock.sendall((json.dumps(hello_json) + "\n").encode('utf-8'))
            
            # Aguarda HELLO_OK
            data = b""
            while b'\n' not in data:
                chunk = sock.recv(4096)
                if not chunk:
                    logger.error(f"Connection closed by {peer.peer_id} before HELLO_OK")
                    sock.close()
                    return False
                data += chunk
            
            line, _ = data.split(b'\n', 1)
            import json
            hello_ok_dict = json.loads(line.decode('utf-8'))
            hello_ok = Message.from_dict(hello_ok_dict)
            
            if hello_ok.msg_type != MessageType.HELLO_OK:
                logger.error(f"Expected HELLO_OK from {peer.peer_id}, got {hello_ok.msg_type.value}")
                sock.close()
                return False
            
            logger.info(f"Connected to {peer.peer_id} (outbound)")
            
            # Cria conexão
            conn = PeerConnection(
                peer.peer_id,
                sock,
                "outbound",
                self._on_message,
                self._on_disconnect
            )
            
            with self.conn_lock:
                self.connections[peer.peer_id] = conn
            
            conn.start()
            
            self.peer_table.mark_connected(peer.peer_id)
            self.state.add_connection(ConnectionInfo(
                peer_id=peer.peer_id,
                direction="outbound",
                connected_at=datetime.now()
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {peer.peer_id}: {e}")
            return False
        finally:
            with self.conn_lock:
                self.connecting_peers.discard(peer.peer_id)
    
    def _on_inbound_connection(self, peer_id: str, sock: socket.socket):
        """Trata conexão de entrada"""
        with self.conn_lock:
            if peer_id in self.connections:
                logger.warning(f"Already have connection with {peer_id}, closing new inbound")
                sock.close()
                return
            
            conn = PeerConnection(
                peer_id,
                sock,
                "inbound",
                self._on_message,
                self._on_disconnect
            )
            
            self.connections[peer_id] = conn
            conn.start()
            
            self.state.add_connection(ConnectionInfo(
                peer_id=peer_id,
                direction="inbound",
                connected_at=datetime.now()
            ))
            
            # Atualiza tabela de peers
            namespace, name = peer_id.split('@')
            peer_info = self.peer_table.get_peer(peer_id)
            if not peer_info:
                # Ainda não conhecemos este peer, adiciona
                peer_info = PeerInfo(
                    peer_id=peer_id,
                    ip="unknown",
                    port=0,
                    namespace=namespace,
                    name=name,
                    status=PeerStatus.CONNECTED
                )
                self.peer_table.peers[peer_id] = peer_info
            else:
                self.peer_table.mark_connected(peer_id)
    
    def _on_disconnect(self, peer_id: str):
        """Trata desconexão de peer"""
        logger.info(f"Peer disconnected: {peer_id}")
        
        with self.conn_lock:
            self.connections.pop(peer_id, None)
        
        self.state.remove_connection(peer_id)
        self.peer_table.mark_disconnected(peer_id)
        self.keep_alive.clear_peer(peer_id)
        self.message_router.clear_peer(peer_id)
    
    def _on_message(self, peer_id: str, message: Message):
        """Trata mensagem recebida de peer"""
        msg_type = message.msg_type
        
        if msg_type == MessageType.PING:
            # Responde com PONG
            pong = Message(
                msg_type=MessageType.PONG,
                msg_id=message.msg_id,
                timestamp=datetime.now().isoformat()
            )
            self._send_message_to_peer(peer_id, pong)
        
        elif msg_type == MessageType.PONG:
            # Trata PONG
            self.keep_alive.handle_pong(peer_id, message.msg_id, self.state.update_peer_rtt)
        
        elif msg_type == MessageType.SEND:
            # Mensagem direta
            print(f"\n[{peer_id}] {message.payload}")
            
            if message.require_ack:
                self.message_router.send_ack(peer_id, message.msg_id)
        
        elif msg_type == MessageType.PUB:
            # Mensagem publicada
            print(f"\n[{peer_id} -> {message.dst}] {message.payload}")
        
        elif msg_type == MessageType.ACK:
            # ACK para mensagem enviada
            self.message_router.handle_ack(peer_id, message.msg_id)
        
        elif msg_type == MessageType.BYE:
            # Peer está saindo
            logger.info(f"Received BYE from {peer_id}: {message.reason}")
            
            # Envia BYE_OK
            bye_ok = Message(
                msg_type=MessageType.BYE_OK,
                msg_id=message.msg_id,
                src=self.peer_id,
                dst=peer_id
            )
            self._send_message_to_peer(peer_id, bye_ok)
            
            # Fecha conexão
            with self.conn_lock:
                conn = self.connections.get(peer_id)
                if conn:
                    conn.stop()
        
        elif msg_type == MessageType.BYE_OK:
            # Peer confirmou nosso BYE
            logger.info(f"Received BYE_OK from {peer_id}")
        
        elif msg_type == MessageType.RELAY:
            # Mensagem de relay - para nós ou para encaminhar
            if message.dst == self.peer_id:
                # Mensagem é para nós - exibe
                print(f"\n[RELAY from {message.src}] {message.payload}")
            else:
                # Encaminha a mensagem de relay
                self.message_router.handle_relay(peer_id, message)
    
    def _send_message_to_peer(self, peer_id: str, message: Message) -> bool:
        """Envia mensagem para um peer específico"""
        with self.conn_lock:
            conn = self.connections.get(peer_id)
            if conn:
                return conn.send_message(message)
            else:
                logger.warning(f"No connection to {peer_id}")
                return False
    
    def _send_bye(self, peer_id: str):
        """Envia BYE para um peer"""
        bye = Message(
            msg_type=MessageType.BYE,
            msg_id=str(uuid.uuid4()),
            src=self.peer_id,
            dst=peer_id,
            reason="Client shutting down"
        )
        self._send_message_to_peer(peer_id, bye)
    
    def _get_connected_peer_ids(self) -> list:
        """Obtém lista de IDs de peers conectados"""
        with self.conn_lock:
            return list(self.connections.keys())
    
    def _get_peers_by_namespace(self, namespace: str) -> list:
        """Obtém peers conectados em um namespace"""
        with self.conn_lock:
            return [
                peer_id for peer_id in self.connections.keys()
                if peer_id.endswith(f"@{namespace}")
            ]
    
    # Manipuladores de Comandos CLI
    
    def _cmd_peers(self, scope: str):
        """Trata comando /peers"""
        if scope == "*":
            peers = self.rendezvous.discover()
        elif scope.startswith("#"):
            namespace = scope[1:]
            peers = self.rendezvous.discover(namespace)
        else:
            print("Invalid scope. Use '*' or '#namespace'")
            return
        
        if not peers:
            print("No peers found")
            return
        
        # Filtra a si mesmo
        peers = [p for p in peers if f"{p['name']}@{p['namespace']}" != self.peer_id]
        
        if not peers:
            print("No other peers found")
            return
        
        print(f"\nDiscovered {len(peers)} peer(s):")
        print("-" * 60)
        for peer in peers:
            peer_id = f"{peer['name']}@{peer['namespace']}"
            status = "CONNECTED" if peer_id in self.connections else "DISCONNECTED"
            print(f"{peer_id:30} {peer['ip']:15}:{peer['port']:5} [{status}]")
        print("-" * 60)
    
    def _cmd_msg(self, peer_id: str, message: str):
        """Trata comando /msg"""
        if peer_id in self.connections:
            # Conexão direta disponível
            self.message_router.send_direct(peer_id, message)
        else:
            # Tenta relay através de outro peer
            print(f"No direct connection to {peer_id}, trying relay...")
            if self.message_router.send_via_relay(peer_id, message):
                print(f"Message sent via relay to {peer_id}")
            else:
                print(f"Failed to send message to {peer_id} - no route available")
    
    def _cmd_pub(self, scope: str, message: str):
        """Trata comando /pub"""
        count = self.message_router.publish(scope, message)
        print(f"Published to {count} peer(s)")
    
    def _cmd_relay(self, peer_id: str, message: str):
        """Trata comando /relay - força envio via relay"""
        if self.message_router.send_via_relay(peer_id, message):
            print(f"Message sent via relay to {peer_id}")
        else:
            print(f"Failed to relay message to {peer_id} - no relay peer available")
    
    def _cmd_conn(self):
        """Trata comando /conn"""
        connections = self.state.get_all_connections()
        
        if not connections:
            print("No active connections")
            return
        
        print(f"\nActive Connections ({len(connections)}):")
        print("-" * 60)
        for peer_id, conn_info in connections.items():
            duration = (datetime.now() - conn_info.connected_at).total_seconds()
            print(f"{peer_id:30} {conn_info.direction:10} {duration:.0f}s")
        print("-" * 60)
    
    def _cmd_rtt(self):
        """Trata comando /rtt"""
        peers = self.peer_table.get_all_peers()
        
        print("\nRTT Statistics:")
        print("-" * 60)
        for peer_id, peer in peers.items():
            if peer.avg_rtt is not None:
                print(f"{peer_id:30} {peer.avg_rtt:.2f} ms")
        print("-" * 60)
    
    def _cmd_reconnect(self):
        """Trata comando /reconnect"""
        self.peer_table.force_reconnect()
        print("Forced reconnection for all disconnected peers")
    
    def _cmd_log(self, level: str):
        """Trata comando /log"""
        try:
            logging.getLogger().setLevel(level)
            print(f"Log level set to {level}")
        except ValueError:
            print(f"Invalid log level: {level}")
    
    def _cmd_quit(self):
        """Trata comando /quit"""
        print("Shutting down...")
        self.stop()
        import sys
        sys.exit(0)
