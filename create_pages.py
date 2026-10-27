"""
RealtorAIGuide blog ekata ona static pages (About, Contact, Privacy Policy, Disclaimer) hadanawa.
Pages draft widihata hadenawa - Blogger dashboard eken check karala publish karanna.

    python create_pages.py
"""

from blogger_publish import get_blog_id, get_service

BLOG = "RealtorAIGuide"

PAGES = {
    "About": f"""
<p>Welcome to <strong>{BLOG}</strong>, a practical guide to using AI tools in real estate.</p>
<p>Real estate agents spend hours on listing descriptions, follow-up emails, social media and lead management.
AI can take a lot of that work off your plate, but there are hundreds of tools and most reviews are vague.
Here we test AI tools, share ready-to-use prompts and write step-by-step tutorials so you can save time and
focus on clients.</p>
<h2>What you'll find here</h2>
<ul>
<li>Honest reviews and comparisons of AI tools for agents and brokers</li>
<li>ChatGPT prompts for listings, emails, scripts and social posts</li>
<li>Tutorials on AI CRMs, chatbots, virtual staging and photo editing</li>
</ul>
<p>We focus on productivity and marketing tools. Nothing on this site is financial, legal or real estate
licensing advice.</p>
""",
    "Contact": f"""
<p>Have a question, a tool you'd like us to review, or a partnership idea? We'd love to hear from you.</p>
<p>Use the contact form in the sidebar of this site and we'll reply as soon as we can, usually within 2-3 business days.</p>
<p>Thanks for reading {BLOG}!</p>
""",
    "Privacy Policy": f"""
<p><em>Last updated: October 27, 2026</em></p>
<p>This Privacy Policy explains how {BLOG} ("we", "us") collects and uses information when you visit this website.</p>
<h2>Information we collect</h2>
<p>We do not ask you to create an account. If you contact us, we receive the name and email address you provide.
Like most websites, our hosting platform (Google Blogger) and analytics tools automatically collect technical data
such as your browser type, device, pages visited and approximate location.</p>
<h2>Cookies</h2>
<p>This site uses cookies from Google and other third parties for analytics and, where enabled, advertising.
Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this and other websites.
You can opt out of personalized advertising at <a href="https://www.google.com/settings/ads">Google Ads Settings</a>
or <a href="https://www.aboutads.info">www.aboutads.info</a>.</p>
<h2>Affiliate links</h2>
<p>Some links on this site are affiliate links. If you buy through them, the merchant may set a cookie to track the referral.</p>
<h2>Your rights</h2>
<p>Depending on where you live (for example California under the CCPA/CPRA), you may have the right to request access to or
deletion of personal information. Contact us using the Contact page to make a request.</p>
<h2>Children</h2>
<p>This site is not directed at children under 13 and we do not knowingly collect their information.</p>
<h2>Changes</h2>
<p>We may update this policy from time to time. Changes will be posted on this page with a new date.</p>
""",
    "Disclaimer": f"""
<h2>Affiliate disclosure</h2>
<p>{BLOG} is reader-supported. Some links on this site are affiliate links, which means we may earn a commission
if you click and make a purchase, at no extra cost to you. This does not influence our reviews; we only recommend
tools we believe are useful. This disclosure is made in accordance with the FTC's guidelines on endorsements.</p>
<h2>No professional advice</h2>
<p>Content on this site is for general information and education about software tools. It is not legal, financial,
tax or real estate brokerage advice. Always follow your brokerage's policies, your state's real estate laws and
fair housing rules when using AI-generated content.</p>
<h2>Accuracy</h2>
<p>AI tools change quickly. Features and prices may have changed since an article was written, so please confirm
details on the vendor's website. Some content on this site is drafted with the help of AI and reviewed before publishing.</p>
<h2>Trademarks</h2>
<p>All product names and trademarks are the property of their respective owners. {BLOG} is not affiliated with
the National Association of REALTORS&reg; or any tool vendor unless stated.</p>
""",
}


def main():
    service = get_service()
    blog_id = get_blog_id(service)
    existing = {p["title"] for p in service.pages().list(blogId=blog_id, status=["DRAFT", "LIVE"]).execute().get("items", [])}
    for title, html in PAGES.items():
        if title in existing:
            print(f"Skip (exists): {title}")
            continue
        page = service.pages().insert(blogId=blog_id, body={"title": title, "content": html.strip()}, isDraft=True).execute()
        print(f"Created draft page: {title}  id={page['id']}")


if __name__ == "__main__":
    main()
