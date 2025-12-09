from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from home.models import Posts, Comment, Article
from onlineshop.models import Product, ProductComment, Category
from utils.utils import exclude_blocked_relations
from .serializers import (
    PostSerializer, CommentSerializer, ArticleSerializer,
    ProductSerializer, ProductCommentSerializer, CategorySerializer
)


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing posts.
    Provides list and detail views, similar to HomepageView.
    """
    queryset = Posts.objects.all()
    serializer_class = PostSerializer
    
    def get_queryset(self):
        """
        Get posts with optional search filtering.
        Similar to HomepageView.get_queryset() but simplified for API.
        """
        queryset = Posts.objects.select_related('user').prefetch_related('hashtags', 'comments__user')
        
        # Search functionality
        search_keyword = self.request.query_params.get('search', None)
        if search_keyword:
            queryset = queryset.filter(
                Q(hashtags__name__icontains=search_keyword) |
                Q(desc__icontains=search_keyword)
            ).distinct()
        
        # User-specific filtering (if authenticated)
        user = self.request.user
        if user.is_authenticated:
            queryset = exclude_blocked_relations(user, queryset)
            if queryset is None:
                queryset = Posts.objects.select_related('user').prefetch_related('hashtags', 'comments__user')
        
        return queryset.order_by('-created')
    
    def get_serializer_context(self):
        """Add request to context for building absolute URLs."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing articles.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    
    def get_queryset(self):
        """Get articles with optional search filtering."""
        queryset = Article.objects.all()
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        return queryset.order_by('-created')
    
    def get_serializer_context(self):
        """Add request to context for building absolute URLs."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing products.
    Provides list and detail views with comments, similar to ProductsListView.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        """
        Get products with optional category and search filtering.
        Similar to ProductsListView.get_queryset().
        """
        queryset = Product.objects.prefetch_related(
            'category', 'comments__user', 'extra_images', 'ratings'
        )
        
        # Category filtering
        category_slug = self.kwargs.get('category_slug', None)
        if not category_slug:
            category_slug = self.request.query_params.get('category', None)
        
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        
        # Search filtering
        search_keyword = self.request.query_params.get('search', None)
        if search_keyword:
            queryset = queryset.filter(title__icontains=search_keyword)
        
        # Sorting
        sort_keyword = self.request.query_params.get('sort_by', None)
        sort_possibilities = ["created", "-created", "-price", "price", "discount"]
        if sort_keyword and sort_keyword in sort_possibilities:
            queryset = queryset.order_by(sort_keyword)
        
        return queryset
    
    def get_serializer_context(self):
        """Add request to context for building absolute URLs."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get all comments for a specific product."""
        product = self.get_object()
        comments = ProductComment.objects.filter(product=product).select_related('user').order_by('-created')
        serializer = ProductCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing product categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    def get_queryset(self):
        """Filter categories if needed."""
        queryset = Category.objects.all()
        is_sub = self.request.query_params.get('is_sub', None)
        if is_sub is not None:
            queryset = queryset.filter(is_sub=is_sub.lower() == 'true')
        return queryset.order_by('name')
