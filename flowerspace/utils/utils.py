from django.core.mail import send_mail
from accounts.models import Relations
from home.models import Posts
import json
import random
import os
from django.conf import settings
import requests
from bs4 import BeautifulSoup
from datetime import date
from django.db.models import Q
from django.core.cache import cache


RECEIVER_EMAIL = 'projectspacedevs@gmail.com'

def send_otp(request, email):
    otp_code = str(random.randint(100000, 999999))
    request.session['otp_code'] = otp_code
    send_mail("Your otp code", f"Flowerspace OTP code for your email: {otp_code}", RECEIVER_EMAIL, [email,])


def verify_otp(saved_code, submitted_code):
    return saved_code == submitted_code



def send_contact_mail(name, email, desc):
    message = f"""
❊❋✽✾✿❀❁❃⚘⚜✤☘ꕥꕤ
from: {name} 
                
email: {email}
                
message: 
{desc}
❊❋✽✾✿❀❁❃⚘⚜✤☘ꕥꕤ
"""
    send_mail(name, message, email, [RECEIVER_EMAIL,])




def exclude_blocked_relations(user, queryset):
    if user.is_authenticated:
        blocked_ids = Relations.objects.filter(from_user=user, is_blocking=True).values_list('to_user_id', flat=True)
        blocked_by_ids = Relations.objects.filter(to_user=user, is_blocking=True).values_list('from_user_id', flat=True)
        excluded_ids = list(blocked_ids) + list(blocked_by_ids)
        return queryset.exclude(user__id__in=excluded_ids).select_related('user')
    return None


def get_daily_quote():
    quotes_path = os.path.join(settings.BASE_DIR, 'quotes.json')
    today_key = f"quote:{date.today()}"
    quote = cache.get(today_key)
    with open(quotes_path, 'r', encoding='utf-8') as f:
        quotes = json.load(f)
    if not quote:
        quote = random.choice(quotes)
        cache.set(today_key, quote, 60 * 60 * 24)  # 1 day
    return quote



def get_or_refresh_news():
    url = 'https://phys.org/earth-news/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    cleaned_obj = BeautifulSoup(response.text, "html.parser")
    articles = []

    for article in cleaned_obj.find_all(class_="sorted-article", limit=10):
        link = article.find("a", class_="news-link")
        img_tag = article.find("img")
        if link and img_tag:
            articles.append({
                "title": link.text,
                "link": link.get("href"),
                "desc": article.find("p").get_text(strip=True),
                "created": article.find("p", class_="text-uppercase text-low").get_text(strip=True),
                "image": img_tag.get("data-src") or img_tag.get("src")
            })
    return articles




class PostsCacheManager:
    CACHE_KEY_ALL = "posts:all"

    @classmethod
    def update_posts(cls):
        posts = list(Posts.objects.all().order_by("?"))
        cache.set(cls.CACHE_KEY_ALL, posts)

    @classmethod
    def get_posts(cls, user=None, search_keyword=None):
        """
        Return cached posts with optional user-specific adjustments.
        Falls back to DB and repopulates cache if empty.
        Always returns a queryset.
        """
        # Search-specific filtering takes priority
        if search_keyword:
            queryset = Posts.objects.filter(
                Q(hashtags__name__icontains=search_keyword) |
                Q(desc__icontains=search_keyword)
            ).distinct().select_related('user').prefetch_related('hashtags')
            
            # Apply blocked relations filtering if user is authenticated
            if user and user.is_authenticated:
                queryset = exclude_blocked_relations(user, queryset)
                if queryset is None:
                    queryset = Posts.objects.none()
            
            return queryset

        # Check cache and update if needed
        posts = cache.get(cls.CACHE_KEY_ALL)
        if posts is None:
            cls.update_posts()

        # User-specific filtering
        if user and user.is_authenticated:
            followed_users = Relations.objects.filter(
                from_user=user, is_blocking=False
            ).values_list("to_user", flat=True)

            newest_following_posts = Posts.objects.filter(
                user__id__in=followed_users
            ).select_related('user').prefetch_related('hashtags').order_by("-created")[:3]

            newest_ids = list(newest_following_posts.values_list('id', flat=True))
            randomized_posts = Posts.objects.exclude(id__in=newest_ids).select_related('user').prefetch_related('hashtags').order_by("?")
            
            # Apply blocked relations filtering
            randomized_posts = exclude_blocked_relations(user, randomized_posts)
            if randomized_posts is None:
                randomized_posts = Posts.objects.none()
            
            # Get IDs from both querysets
            following_ids = list(newest_following_posts.values_list('id', flat=True))
            random_ids = list(randomized_posts.values_list('id', flat=True))
            all_ids = following_ids + random_ids
            
            if all_ids:
                # Combine querysets by IDs, maintaining order (following posts first)
                queryset = Posts.objects.filter(id__in=all_ids).select_related('user').prefetch_related('hashtags')
                # Preserve order: following posts first, then randomized
                from django.db.models import Case, When, IntegerField
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(all_ids)])
                queryset = queryset.annotate(order=preserved).order_by('order')
            else:
                queryset = Posts.objects.none()
            
            return queryset

        # For non-authenticated users, return all posts (use cache if available)
        return Posts.objects.all().select_related('user').prefetch_related('hashtags').order_by("?")

    @classmethod
    def invalidate_cache(cls):
        """Clear the cached posts (use in signals)."""
        cache.delete(cls.CACHE_KEY_ALL)