import redis
import json
import hashlib
from datetime import datetime
from django.conf import settings


redis_url = settings.REDIS_URL

class RedisClient:
    """Singleton Redis connection."""
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            if redis_url is None:
                raise ValueError(
                    "REDIS_URL is not set. Please set REDIS_URL in your environment variables "
                    "or Django settings (e.g., 'redis://localhost:6379/0')"
                )
            cls._connection = redis.Redis.from_url(redis_url)
        return cls._connection


class BaseRepository:
    def __init__(self):
        self.redis = RedisClient.get_connection()

    def _set(self, key, value):
        self.redis.set(key, json.dumps(value))

    def _get(self, key):
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def _delete(self, key):
        self.redis.delete(key)

    def get_key(self, entity: str, entity_id: int, suffix: str) -> str:
        """Generate a consistent Redis key."""
        return f"{entity}:{entity_id}:{suffix}"

    def add(self, key1, key2):
        """Add bidirectional relation (user<->object)."""
        self.redis.sadd(key1, key2)

    def remove(self, key1, key2):
        """Remove bidirectional relation (user<->object)."""
        self.redis.srem(key1, key2)


    def toggle(self, key1, key2):
        """Toggle add/remove relationship."""
        if self.redis.sismember(key1, key2):
            self.remove(key1, key2)
            return "removed"
        else:
            self.add(key1, key2)
            return "added"


class LikesRepository(BaseRepository):
    """Handle likes in Redis (user <-> post mapping). methods return a LIST"""

    def toggle_like(self, user_id, post_id):
        user_key = self.get_key("user", user_id, "likes")
        post_key = self.get_key("post", post_id, "liked_by")
        user_action = self.toggle(user_key, post_id)
        self.toggle(post_key, user_id)  # mirror
        return user_action

    def get_likes_for_user(self, user_id):
        key = self.get_key("user", user_id, "likes")
        return [int(post_id) for post_id in self.redis.smembers(key)]

    def get_likes_for_post(self, post_id):
        key = self.get_key("post", post_id, "liked_by")
        return [int(user_id) for user_id in self.redis.smembers(key)]


class BookmarkRepository(BaseRepository):
    """Handle bookmarks in Redis (user <-> post mapping). methods return a LIST"""

    def toggle_bookmark(self, user_id, post_id):
        user_key = self.get_key("user", user_id, "bookmarks")
        post_key = self.get_key("post", post_id, "bookmarked_by")
        user_action = self.toggle(user_key, post_id)
        self.toggle(post_key, user_id)  # mirror
        return user_action

    def get_bookmarks_for_user(self, user_id):
        key = self.get_key("user", user_id, "bookmarks")
        return [int(post_id) for post_id in self.redis.smembers(key)]

    def get_bookmarks_for_post(self, post_id):
        key = self.get_key("post", post_id, "bookmarked_by")
        return [int(user_id) for user_id in self.redis.smembers(key)]



class Notification:
    def __init__(self, from_user, message, target_type=None, target_id=None, created=None):
        self.from_user = from_user
        self.message = message
        self.target_type = target_type
        self.target_id = target_id
        self.created = created or datetime.utcnow()

        # unique signature for spam-prevention
        self.signature = self._make_signature()

    def _make_signature(self):
        base = f"{self.from_user}:{self.target_type}:{self.target_id}"
        return hashlib.sha1(base.encode()).hexdigest()

    def to_json(self):
        return json.dumps({
            "from_user": self.from_user,
            "message": self.message,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "created": self.created.isoformat(),
            "signature": self.signature,
        })


class NotificationRepository(BaseRepository):
    """Handles notification system for users. methods return a list of Notification objects."""

    def add_notification(self, user_id, notif: Notification):
        key = self.get_key("user", user_id, "notifications")
        notif_json = json.dumps({
            "from_user": notif.from_user,
            "message": notif.message,
            "created": notif.created.isoformat(),
        })

        # pull latest notifs and check for same signature
        existing = self.redis.lrange(key, 0, -1)
        for item in existing:
            data = json.loads(item)
            if data.get("signature") == notif.signature:
                return  # duplicate → ignore

        self.redis.lpush(key, notif.to_json())
        self.redis.ltrim(key, 0, 20)

    def get_notifications(self, user_id):
        key = self.get_key("user", user_id, "notifications")
        raw_notifs = self.redis.lrange(key, 0, -1)
        notifications = []
        for n in raw_notifs:
            data = json.loads(n)
            notifications.append(
                Notification(
                    from_user=data["from_user"],
                    message=data["message"],
                    created=datetime.fromisoformat(data["created"]),
                    target_type=data.get("target_type"),
                    target_id=data.get("target_id"),
                ))
        return notifications

    def clear_notifications(self, user_id):
        key = self.get_key("user", user_id, "notifications")
        self.redis.delete(key)


