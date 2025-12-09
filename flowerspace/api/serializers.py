from rest_framework import serializers
from django.contrib.auth.models import User
from home.models import Posts, Comment, Hashtag, Article
from onlineshop.models import Product, ProductComment, ProductRating, Category, ProductImage
from utils.redis_manager import LikesRepository


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for nested representations."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class HashtagSerializer(serializers.ModelSerializer):
    """Serializer for hashtags."""
    class Meta:
        model = Hashtag
        fields = ['id', 'name']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for post comments."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'created']


class PostSerializer(serializers.ModelSerializer):
    """Main serializer for posts with related data."""
    user = UserSerializer(read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Posts
        fields = [
            'id', 'image', 'image_url', 'desc', 'user', 'hashtags',
            'allow_comments', 'created', 'updated', 'comments', 'likes_count'
        ]
    
    def get_comments(self, obj):
        """Get all comments for this post."""
        comments = Comment.objects.filter(post=obj).select_related('user').order_by('-created')
        return CommentSerializer(comments, many=True).data
    
    def get_likes_count(self, obj):
        """Get likes count from Redis."""
        redis_class = LikesRepository()
        return len(redis_class.get_likes_for_post(post_id=obj.id))
    
    def get_image_url(self, obj):
        """Get full image URL."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ArticleSerializer(serializers.ModelSerializer):
    """Serializer for articles."""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = ['id', 'image', 'image_url', 'title', 'author', 'desc', 'created', 'updated']
    
    def get_image_url(self, obj):
        """Get full image URL."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'is_sub']


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product extra images."""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'uploaded']
    
    def get_image_url(self, obj):
        """Get full image URL."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductCommentSerializer(serializers.ModelSerializer):
    """Serializer for product comments."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ProductComment
        fields = ['id', 'user', 'text', 'recently_bought_product', 'created']


class ProductSerializer(serializers.ModelSerializer):
    """Main serializer for products with related data."""
    category = CategorySerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    extra_images = ProductImageSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    like_percentage = serializers.SerializerMethodField()
    ratings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'image', 'image_url', 'description',
            'price', 'discount', 'discount_price', 'available', 'created', 'updated',
            'category', 'comments', 'extra_images', 'like_percentage', 'ratings_count'
        ]
    
    def get_comments(self, obj):
        """Get all comments for this product."""
        comments = ProductComment.objects.filter(product=obj).select_related('user').order_by('-created')
        return ProductCommentSerializer(comments, many=True).data
    
    def get_image_url(self, obj):
        """Get full image URL."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_discount_price(self, obj):
        """Calculate discount price if discount exists."""
        if obj.discount:
            return int(obj.price - ((obj.discount / 100) * obj.price))
        return obj.price
    
    def get_like_percentage(self, obj):
        """Get like percentage from ratings."""
        return obj.get_like_percentage()
    
    def get_ratings_count(self, obj):
        """Get total ratings count."""
        return obj.ratings.count()

