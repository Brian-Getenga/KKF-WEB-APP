# apps/newsletter/email_templates.py - CORRECTED VERSION

from django.utils.html import escape

def get_email_template(campaign_type, content_object=None):
    """
    Get email template based on campaign type
    """
    
    if campaign_type == 'new_class':
        return get_new_class_template(content_object)
    elif campaign_type == 'new_instructor':
        return get_new_instructor_template(content_object)
    elif campaign_type == 'blog_post':
        return get_blog_post_template(content_object)
    elif campaign_type == 'event':
        return get_event_template(content_object)
    else:
        return get_default_template()


def get_new_class_template(karate_class):
    """Template for new class announcement"""
    return f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; margin-bottom: 20px;">New Class Alert! 🥋</h1>
            
            <h2 style="color: #525252; margin-bottom: 10px;">{escape(karate_class.title)}</h2>
            
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Level:</strong> {escape(karate_class.level)}</p>
                <p style="margin: 5px 0;"><strong>Category:</strong> {escape(karate_class.get_category_display())}</p>
                <p style="margin: 5px 0;"><strong>Instructor:</strong> {escape(karate_class.instructor.name) if karate_class.instructor else 'TBA'}</p>
                <p style="margin: 5px 0;"><strong>Price:</strong> KES {karate_class.price}</p>
                <p style="margin: 5px 0;"><strong>Duration:</strong> {karate_class.duration_minutes} minutes</p>
            </div>
            
            <p style="color: #333333; line-height: 1.6; margin: 20px 0;">
                {escape(karate_class.description[:200])}...
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{{{{ class_url }}}}" style="display: inline-block; padding: 12px 30px; background-color: #FF6B00; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    View Class Details
                </a>
            </div>
            
            <p style="color: #666666; font-size: 12px; margin-top: 30px; text-align: center;">
                You're receiving this because you subscribed to our newsletter.
                <a href="{{{{ unsubscribe_url }}}}" style="color: #FF6B00;">Unsubscribe</a>
            </p>
        </div>
    </div>
    '''


def get_new_instructor_template(instructor):
    """Template for new instructor announcement"""
    return f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; margin-bottom: 20px;">Welcome Our New Instructor! 🥋</h1>
            
            <h2 style="color: #525252; margin-bottom: 10px;">{escape(instructor.name)}</h2>
            
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Rank:</strong> {escape(instructor.get_rank_display())}</p>
                <p style="margin: 5px 0;"><strong>Experience:</strong> {instructor.experience_years} years</p>
                <p style="margin: 5px 0;"><strong>Specialization:</strong> {escape(instructor.get_specialization_display())}</p>
            </div>
            
            <p style="color: #333333; line-height: 1.6; margin: 20px 0;">
                {escape(instructor.short_bio) if instructor.short_bio else escape(instructor.bio[:200])}...
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{{{{ instructor_url }}}}" style="display: inline-block; padding: 12px 30px; background-color: #FF6B00; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Meet {escape(instructor.name.split()[0])}
                </a>
            </div>
            
            <p style="color: #666666; font-size: 12px; margin-top: 30px; text-align: center;">
                You're receiving this because you subscribed to our newsletter.
                <a href="{{{{ unsubscribe_url }}}}" style="color: #FF6B00;">Unsubscribe</a>
            </p>
        </div>
    </div>
    '''


def get_blog_post_template(blog_post):
    """Template for new blog post announcement"""
    author_name = ""
    if blog_post.author:
        if hasattr(blog_post.author, 'get_full_name'):
            author_name = blog_post.author.get_full_name()
        elif hasattr(blog_post.author, 'full_name'):
            author_name = blog_post.author.full_name
        else:
            author_name = str(blog_post.author)
    
    return f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; margin-bottom: 20px;">New Blog Post 📝</h1>
            
            <h2 style="color: #525252; margin-bottom: 10px;">{escape(blog_post.title)}</h2>
            
            {f'<p style="color: #999999; font-size: 14px; margin: 10px 0;"><strong>By:</strong> {escape(author_name)}</p>' if author_name else ''}
            
            <p style="color: #333333; line-height: 1.6; margin: 20px 0;">
                {escape(blog_post.excerpt) if blog_post.excerpt else escape(blog_post.content[:200])}...
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{{{{ post_url }}}}" style="display: inline-block; padding: 12px 30px; background-color: #FF6B00; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Read Full Article
                </a>
            </div>
            
            <p style="color: #666666; font-size: 12px; margin-top: 30px; text-align: center;">
                You're receiving this because you subscribed to our newsletter.
                <a href="{{{{ unsubscribe_url }}}}" style="color: #FF6B00;">Unsubscribe</a>
            </p>
        </div>
    </div>
    '''


def get_event_template(event):
    """Template for event announcement"""
    return f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; margin-bottom: 20px;">Upcoming Event! 📅</h1>
            
            <h2 style="color: #525252; margin-bottom: 10px;">{escape(event.get('title', 'Event'))}</h2>
            
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Date:</strong> {escape(str(event.get('date', 'TBA')))}</p>
                <p style="margin: 5px 0;"><strong>Location:</strong> {escape(event.get('location', 'TBA'))}</p>
            </div>
            
            <p style="color: #333333; line-height: 1.6; margin: 20px 0;">
                {escape(event.get('description', 'More details coming soon!'))}
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{{{{ event_url }}}}" style="display: inline-block; padding: 12px 30px; background-color: #FF6B00; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Learn More
                </a>
            </div>
            
            <p style="color: #666666; font-size: 12px; margin-top: 30px; text-align: center;">
                You're receiving this because you subscribed to our newsletter.
                <a href="{{{{ unsubscribe_url }}}}" style="color: #FF6B00;">Unsubscribe</a>
            </p>
        </div>
    </div>
    '''


def get_default_template():
    """Default template for general announcements"""
    return '''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h1 style="color: #1a1a1a; margin-bottom: 20px;">News from Your Karate School 🥋</h1>
            
            <p style="color: #333333; line-height: 1.6; margin: 20px 0;">
                {{ content }}
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{{ website_url }}" style="display: inline-block; padding: 12px 30px; background-color: #FF6B00; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Visit Our Website
                </a>
            </div>
            
            <p style="color: #666666; font-size: 12px; margin-top: 30px; text-align: center;">
                You're receiving this because you subscribed to our newsletter.
                <a href="{{ unsubscribe_url }}" style="color: #FF6B00;">Unsubscribe</a>
            </p>
        </div>
    </div>
    '''