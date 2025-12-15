
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
import os

class DatabaseManager:
    def __init__(self, db_path="vision_assistant.db"):
        """Inicializa la conexión a SQLite"""
        self.db_path = db_path
        print(f"📂 Usando SQLite: {db_path}")
        self._init_database()
    
    def _get_connection(self):
        """Obtiene una conexión a SQLite"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Inicializa las tablas necesarias"""
        commands = [
            # Tabla de usuarios
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                voice_preference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Tabla de detecciones
            """
            CREATE TABLE IF NOT EXISTS detections (
                detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                objects_detected TEXT NOT NULL,
                description TEXT NOT NULL,
                description_hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Tabla de descripciones cacheadas
            """
            CREATE TABLE IF NOT EXISTS cached_descriptions (
                cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                objects_hash TEXT UNIQUE NOT NULL,
                objects_data TEXT NOT NULL,
                description TEXT NOT NULL,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for command in commands:
                    cursor.execute(command)
                
                # Índices
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_created ON detections(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_objects_hash ON cached_descriptions(objects_hash)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_last_used ON cached_descriptions(last_used)")
                
                # Usuario por defecto
                cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (1, 'usuario_default')")
                
                conn.commit()
                print("✅ Base de datos SQLite inicializada")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            raise
    
    def save_detection(self, detections: List[Dict], description: str, user_id: int = 1):
        """Guarda una detección"""
        if not detections or not description:
            return None
        
        description_hash = hashlib.sha256(description.encode()).hexdigest()
        
        # Verificar si ya existe
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT detection_id FROM detections WHERE description_hash = ?",
                (description_hash,)
            )
            if cursor.fetchone():
                return None
        
        # Guardar
        objects_json = json.dumps(detections, default=str)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO detections (user_id, objects_detected, description, description_hash)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, objects_json, description, description_hash)
            )
            detection_id = cursor.lastrowid
            conn.commit()
            
            # Actualizar caché
            self._update_cache(detections, description)
            
            return detection_id
    
    def get_cached_description(self, detections: List[Dict]) -> Optional[str]:
        """Obtiene una descripción cacheada"""
        if not detections:
            return None
        
        objects_str = json.dumps(detections, sort_keys=True, default=str)
        objects_hash = hashlib.sha256(objects_str.encode()).hexdigest()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT description FROM cached_descriptions WHERE objects_hash = ?",
                (objects_hash,)
            )
            result = cursor.fetchone()
            
            if result:
                cursor.execute(
                    """
                    UPDATE cached_descriptions 
                    SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                    WHERE objects_hash = ?
                    """,
                    (objects_hash,)
                )
                conn.commit()
                return result['description']
        
        return None
    
    def _update_cache(self, detections: List[Dict], description: str):
        """Actualiza la caché"""
        objects_str = json.dumps(detections, sort_keys=True, default=str)
        objects_hash = hashlib.sha256(objects_str.encode()).hexdigest()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cached_descriptions (objects_hash, objects_data, description)
                VALUES (?, ?, ?)
                ON CONFLICT(objects_hash) 
                DO UPDATE SET 
                    usage_count = usage_count + 1,
                    last_used = CURRENT_TIMESTAMP
                """,
                (objects_hash, json.dumps(detections, default=str), description)
            )
            conn.commit()
    
    def get_user_preferences(self, user_id: int = 1) -> Dict:
        """Obtiene preferencias del usuario"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT voice_preference FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result and result['voice_preference']:
                return json.loads(result['voice_preference'])
        
        return {'volume': 0.7, 'rate': 150, 'language': 'es'}
    
    def save_user_preferences(self, preferences: Dict, user_id: int = 1):
        """Guarda preferencias"""
        preferences_json = json.dumps(preferences)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (user_id, voice_preference)
                VALUES (?, ?)
                ON CONFLICT(user_id) 
                DO UPDATE SET voice_preference = ?
                """,
                (user_id, preferences_json, preferences_json)
            )
            conn.commit()
    
    def get_detection_history(self, limit: int = 100, user_id: int = 1) -> List[Dict]:
        """Obtiene historial"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT description, created_at
                FROM detections
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def cleanup_cache(self, days_to_keep: int = 30):
        """Limpia caché antigua"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM cached_descriptions
                WHERE last_used < datetime('now', '-? days')
                AND usage_count < 5
                """,
                (days_to_keep,)
            )
            conn.commit()
