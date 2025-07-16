import praw
import requests
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import os

# Reddit API 配置
# 需要在 https://www.reddit.com/prefs/apps 创建应用获取
REDDIT_CONFIG = {
    'client_id': 'YOUR_CLIENT_ID',
    'client_secret': 'YOUR_CLIENT_SECRET',
    'user_agent': 'MemeBot 1.0'
}

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender': 'your_email@gmail.com',
    'password': 'your_app_password',  # Gmail 需要使用应用专用密码
    'receiver': 'receiver@gmail.com'
}

class RedditMemeCrawler:
    def __init__(self):
        # 初始化 Reddit 客户端
        self.reddit = praw.Reddit(
            client_id=REDDIT_CONFIG['client_id'],
            client_secret=REDDIT_CONFIG['client_secret'],
            user_agent=REDDIT_CONFIG['user_agent']
        )
        
        # 要爬取的 subreddit 列表
        self.subreddits = ['memes', 'dankmemes', 'me_irl', 'wholesomememes']
        
    def calculate_hotness_score(self, post, current_time):
        """计算梗图热度分数"""
        # 获取发布时间差（小时）
        post_age_hours = (current_time - post.created_utc) / 3600
        
        # 时间衰减系数（24小时内的权重更高）
        time_decay = 1.0 if post_age_hours < 24 else 0.5
        
        # 热度分数计算
        score = (
            post.score * 0.4 +  # Reddit 分数（赞踩差值）
            post.num_comments * 0.3 * 10 +  # 评论数（乘以10来平衡权重）
            post.upvote_ratio * 0.3 * 1000  # 好评率
        ) * time_decay
        
        return score
    
    def get_top_memes(self, limit=10):
        """获取今日最热梗图"""
        all_memes = []
        current_time = datetime.now().timestamp()
        
        for subreddit_name in self.subreddits:
            print(f"正在爬取 r/{subreddit_name}...")
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # 获取热门帖子
            for post in subreddit.hot(limit=25):
                # 只获取图片类型的帖子
                if post.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    meme_data = {
                        'title': post.title,
                        'url': post.url,
                        'reddit_url': f"https://reddit.com{post.permalink}",
                        'subreddit': subreddit_name,
                        'score': post.score,
                        'comments': post.num_comments,
                        'upvote_ratio': post.upvote_ratio,
                        'created_time': datetime.fromtimestamp(post.created_utc),
                        'hotness_score': self.calculate_hotness_score(post, current_time)
                    }
                    all_memes.append(meme_data)
        
        # 按热度分数排序
        all_memes.sort(key=lambda x: x['hotness_score'], reverse=True)
        
        # 返回前N个
        return all_memes[:limit]
    
    def generate_email_content(self, memes):
        """生成邮件内容"""
        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                h1 { color: #ff4500; text-align: center; }
                .meme-item { margin-bottom: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 8px; }
                .meme-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
                .meme-img { max-width: 100%; height: auto; border-radius: 5px; }
                .meme-stats { margin-top: 10px; color: #666; font-size: 14px; }
                .meme-link { color: #ff4500; text-decoration: none; }
                .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔥 今日最梗 TOP 10 🔥</h1>
                <p style="text-align: center; color: #666;">由梗图情报局为您精选</p>
        """
        
        for i, meme in enumerate(memes, 1):
            html_content += f"""
                <div class="meme-item">
                    <div class="meme-title">#{i} {meme['title']}</div>
                    <img class="meme-img" src="{meme['url']}" alt="{meme['title']}">
                    <div class="meme-stats">
                        📊 热度分: {meme['hotness_score']:.0f} | 
                        👍 {meme['score']} | 
                        💬 {meme['comments']} 条评论 | 
                        📍 r/{meme['subreddit']}
                    </div>
                    <a class="meme-link" href="{meme['reddit_url']}">查看原帖 →</a>
                </div>
            """
        
        html_content += """
                <div class="footer">
                    <p>每天定时推送最新梗图，让快乐不迟到！</p>
                    <p>生成时间：""" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_email(self, memes):
        """发送邮件"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎉 今日最梗 TOP 10 - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = EMAIL_CONFIG['receiver']
        
        # 生成邮件内容
        html_content = self.generate_email_content(memes)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # 发送邮件
        try:
            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
                server.send_message(msg)
            print(f"邮件发送成功！时间：{datetime.now()}")
        except Exception as e:
            print(f"邮件发送失败：{e}")
    
    def save_to_json(self, memes):
        """保存数据到 JSON 文件（备份）"""
        filename = f"memes_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(memes, f, ensure_ascii=False, indent=2, default=str)
        print(f"数据已保存到 {filename}")
    
    def run_crawler(self):
        """运行爬虫主流程"""
        print("开始爬取 Reddit 梗图...")
        memes = self.get_top_memes(limit=10)
        
        if memes:
            # 保存数据
            self.save_to_json(memes)
            
            # 发送邮件
            self.send_email(memes)
            
            # 打印结果
            print("\n今日 TOP 3 预览：")
            for i, meme in enumerate(memes[:3], 1):
                print(f"{i}. {meme['title']}")
                print(f"   热度分: {meme['hotness_score']:.0f}")
                print(f"   链接: {meme['reddit_url']}\n")
        else:
            print("没有找到合适的梗图")

def schedule_daily_crawl():
    """设置定时任务"""
    crawler = RedditMemeCrawler()
    
    # 每天早上 9 点发送
    schedule.every().day.at("09:00").do(crawler.run_crawler)
    
    # 每天下午 6 点发送
    schedule.every().day.at("18:00").do(crawler.run_crawler)
    
    print("梗图爬虫已启动，等待定时任务...")
    print("定时发送时间：每天 9:00 和 18:00")
    
    # 立即运行一次测试
    crawler.run_crawler()
    
    # 保持运行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    # 单次运行测试
    crawler = RedditMemeCrawler()
    crawler.run_crawler()
    
    # 如果要启动定时任务，取消下面的注释
    # schedule_daily_crawl()
