# 🌸 Flower Space 🌸

**A Social Media Platform for Plant Lovers**

[See demo here](https://flower-space-xi.vercel.app/)
currently unavailable due to vercel limitations

## Table of Contents
- [Update Log](#update-log)
- [Note](#note)
- [About](#about)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)



## 📅 Update Log

### Latest Updates
- **Added Earth News Section**: Integrated a news section to articles using Yetiests and BeautifulSoup for dynamic content.
- **Updated Relations Model**: Introduced block logic between users for improved user management.
- **Product Enhancements**: Added comment and rating sections, support for multiple images, and discount application via updates.
- **Notification System**: Users now receive notifications for published public coupons.
- **Bug Fixes**: Resolved visual bugs using HTML adjustments.
- **Performance Improvements**: Modified feature structure and performance optimizations.
- **New Feature**: Implemented an inner plant-themed quote system that updates daily.


## NOTE:
**REGISTER SYSTEM FINALLY WORKS, OTP CODES WILL BE SENT TO YOUR EMAIL.**
**IF YOU DO NOT WANT TO REGISTER LOGIN WITH: testuser@gmail.com ------ FlowerSpace99**

## 🌿 About

Flower Space is a vibrant social media platform designed for plant enthusiasts to share their botanical journeys, connect with fellow gardeners, and grow their green communities. From sharing plant photos to discussing gardening tips, Flower Space brings nature lovers together.

## ✨ Features

### 🌱 Core Features
- **Post Creation**: Share your plant photos with descriptions and hashtags
- **Likes & Comments**: Engage with other users' posts
- **Bookmarks**: Save your favorite posts for later
- **Articles**: Read and share gardening articles (including a new earth news section using Yetiests and BeautifulSoup)
- **User Profiles**: Showcase your plant collection and gardening expertise

### 🌸 Advanced Features
- **Real-time Notifications**: Stay updated with likes, comments, and public coupon publications
- **Hashtag System**: Discover content through tags
- **Profile Customization**: Edit your profile picture and bio
- **Follow System**: Connect with other plant lovers
- **Product Management**: Add, update, and delete products with comment and rating sections
- **Multiple Images**: Store multiple images per product
- **Discounts**: Apply discounts to products via updates

## 🛠️ Technology Stack

### Backend
- **Django**: Python web framework
- **postgresSQL**: Relational database
- **ArvanCloud**: Outer storage
- **Requests and BS4**: Web scrapping earth news
- **Vercel**: Hosting server
  

### Frontend
- **HTML5 & CSS3**: Responsive design with custom animations
- **JavaScript**: Interactive UI components
- **Font Awesome**: Beautiful icons

## 📂 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/flower-space.git
   cd flower-space
   ```

2. Set up virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up database:
   ```bash
   python manage.py migrate
   ```

5. Run development server:
   ```bash
   python manage.py runserver
   ```


