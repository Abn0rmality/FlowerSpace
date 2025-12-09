from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View, TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from .signals import create_like_notification
from django.contrib.auth.decorators import login_required
from utils.redis_manager import LikesRepository, BookmarkRepository
from .forms import CreatePostForm, CommentForm, ContactForm
from .models import Hashtag, Posts, Comment, Article
from utils.utils import send_contact_mail, exclude_blocked_relations, get_daily_quote, get_or_refresh_news, PostsCacheManager
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from datetime import date
from django.core.cache import cache



class HomepageView(ListView):
    model = Posts
    template_name = "home/homepage.html"
    context_object_name = "posts"

    def get_queryset(self):
        """Get posts using PostsCacheManager, ensuring we always return a queryset."""
        queryset = PostsCacheManager.get_posts(
            user=self.request.user,
            search_keyword=self.request.GET.get("search")
        )
        # Ensure we have a queryset (not None)
        if queryset is None:
            queryset = Posts.objects.none()
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context["daily_quote"] = get_daily_quote()
        return context



class CreatePostView(LoginRequiredMixin, View):
    form_class = CreatePostForm
    template_class = 'home/post_create.html'

    def get(self, request):
        return render(request, self.template_class, {"form":self.form_class})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            hashtags = form.cleaned_data.get('hashtags', [])
            for tag in hashtags:
                hashtag_obj, _ = Hashtag.objects.get_or_create(name=tag)
                post.hashtags.add(hashtag_obj)
            return redirect("home:homepage")
        return render(request, self.template_class, {'form': form})


class PostDeleteView(View):
    def get(self, request, pk):
        post = get_object_or_404(Posts, id=pk)
        if post.user != request.user:
            messages.error(request, "You are not allowed to perform this action.")
            return redirect("home:homepage")
        post.delete()
        messages.success(request, "Post deleted successfully!")
        return redirect("home:homepage")


class PostDetailsView(DetailView):
    model = Posts
    template_name = "home/post_details.html"
    context_object_name = "post"
    pk_url_kwarg = "post_id"

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if not post.allow_comments and request.method == "POST":
            messages.error(request, "A feisty one, aren't you?")
            return redirect("home:homepage")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CommentForm()
        comments = Comment.objects.filter(post=self.get_object()).select_related("user")
        if self.request.user.is_authenticated:
            context["comments"] = exclude_blocked_relations(self.request.user, comments)
        else:
            context["comments"] = comments
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = CommentForm(request.POST)
        post = self.get_object()
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.user = request.user
            new_comment.post = post
            new_comment.save()
            messages.success(request, "Comment has been successfully added!")
            return redirect("home:post_details", post.id)
        return self.render_to_response(self.get_context_data(form=form))


class ToggleLikeView(LoginRequiredMixin, View):
    redis_class = LikesRepository()

    def post(self, request, id):
        post = get_object_or_404(Posts, id=id)
        action = self.redis_class.toggle_like(user_id=request.user.id, post_id=id)
        if action == "added":
            create_like_notification(request.user.id, post.user.id, post.pk, request.user.username)
        liked = action == "added"
        like_count = len(self.redis_class.get_likes_for_post(post_id=id))
        return JsonResponse({"liked": liked, "like_count": like_count})



class ToggleBookmarkView(LoginRequiredMixin, View):
    redis_class = BookmarkRepository()

    def post(self, request, id):
        post = get_object_or_404(Posts, id=id)
        action = self.redis_class.toggle_bookmark(user_id=request.user.id, post_id=id)
        bookmarked = action == "added"
        return JsonResponse({"bookmarked": bookmarked})



class ArticleView(ListView):
    model = Article
    template_name = "home/articles.html"
    context_object_name = "articles"

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        return queryset


class ArticleDetailsView(DetailView):
    model = Article
    template_name = "home/articles_details.html"
    context_object_name = "article"
    pk_url_kwarg = "article_id"


class ContactUsView(LoginRequiredMixin, FormView):
    template_name = 'home/contact_us.html'
    form_class = ContactForm
    success_url = reverse_lazy('home:contact')

    @method_decorator(ratelimit(key='post:email', rate='1/h', method='POST', block=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'email': self.request.user.email}
        return kwargs

    def form_valid(self, form):
        cd = form.cleaned_data
        send_contact_mail(cd['name'], self.request.user.email, cd['message'])
        messages.success(self.request, "Your message had been sent successfully!")
        return redirect('home:contact')




class EarthNewsView(TemplateView):
    template_name = 'home/earth_news.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        today = str(date.today())
        cached_news = cache.get(f"plant_news_{today}")
        if not cached_news:
            news = get_or_refresh_news()
            cache.set(f"plant_news_{today}", news, timeout=86400)
        else:
            news = cached_news

        context["plant_news"] = news
        return context