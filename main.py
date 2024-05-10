import praw
import re
import tkinter as tk
from tkinter import messagebox
import anthropic

client = anthropic.Anthropic(
    api_key="INSERT_API_KEY",
)

reddit = praw.Reddit(client_id='INSERT_CLIENT_ID',
                     client_secret='INSERT_CLINET_SECRET',
                     user_agent='INSERT_USER_AGENT')


def gui():
    app = tk.Tk()
    app.title("Post Submission Tool")
    app.geometry("800x650") 

    frame = tk.Frame(app)
    frame.pack(padx=20, pady=20, expand=True, fill='both')

    # Content of the post
    label_content = tk.Label(frame, text="Content of the post (optional):")
    label_content.grid(row=0, column=0, sticky='nw', padx=10, pady=10)
    content_text = tk.Entry(frame, width=50)
    content_text.grid(row=0, column=1, padx=10, pady=10)

    # Link of the post
    label_link = tk.Label(frame, text="Link of the post to reply to:")
    label_link.grid(row=1, column=0, sticky='nw', padx=10, pady=10)
    link_text = tk.Entry(frame, width=50)
    link_text.grid(row=1, column=1, padx=10, pady=10)

    # Topic of the post
    label_topic = tk.Label(
        frame, text="Or, the topic the post should reference:")
    label_topic.grid(row=2, column=0, sticky='nw', padx=10, pady=10)
    topic_text = tk.Entry(frame, width=50)
    topic_text.grid(row=2, column=1, padx=10, pady=10)

    # Persona
    label_persona = tk.Label(frame, text="Persona (optional):")
    label_persona.grid(row=3, column=0, sticky='nw', padx=10, pady=10)
    persona_text = tk.Entry(frame, width=50)
    persona_text.grid(row=3, column=1, padx=10, pady=10)

    # Slider for informality percentage
    informality_scale = tk.Scale(
        frame, from_=0, to=100, orient='horizontal', length=400, resolution=1, label='Informality %')
    informality_scale.grid(row=5, column=1, sticky='w', padx=10, pady=10)

    # Submit button
    submit_button = tk.Button(frame, text="Submit", command=lambda: submit(
        content_text, link_text, topic_text, persona_text, informality_scale, scrollable_frame, submit_button, canvas))
    submit_button.grid(row=6, column=1, pady=20)
    
    # Scrollable frame for displaying posts
    post_frame = tk.Frame(app)
    post_frame.pack(padx=20, pady=5, expand=True, fill='both')
    canvas = tk.Canvas(post_frame)
    scrollbar = tk.Scrollbar(post_frame, orient='vertical', command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    app.mainloop()

# Function to validate URL
def validate_url(url):
    pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return bool(re.match(pattern, url))

def submit(content_text, link_text, topic_text, persona_text, informality_scale, scrollable_frame, submit_button, canvas):
    try:
        # Removes items in post frame 
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        canvas.update()
    
        submit_button.config(state='disabled', text="Generating...")
        submit_button.update()  

        # Get the values from the form
        content = content_text.get().strip()
        link = link_text.get().strip()
        topic = topic_text.get().strip()
        persona = persona_text.get().strip()
        informality_percentage = informality_scale.get()
        reply = False  # Initialize reply to False

        # Form validation
        if link and not validate_url(link):
            messagebox.showwarning("Invalid Link", "Please enter a valid URL.")
            return
        if not link and not topic:
            messagebox.showwarning("Empty Fields", "Please enter either a link or a topic.")
            return
        if link and topic:
            messagebox.showwarning("Multiple Fields", "Please enter either a link or a topic, not both.")
            return

        # Generate topic from link if provided
        if link:
            post_id = extract_post_id(link)
            if not post_id:
                messagebox.showwarning("Invalid Link", "Please enter a valid Reddit post URL.")
                return
            reply = True
            topic = process_post(post_id)

        prompt = generate_prompt(reply=reply, informality_percentage=informality_percentage, topic=topic,
                                 persona=persona, content=content)
        posts = generate_post(prompt)
        add_posts(posts, scrollable_frame)

    finally:
        submit_button.config(state='normal', text="Submit", bg='systemButtonFace', fg='black')
        submit_button.update()  

def add_posts(posts, scrollable_frame):
    for i, post in enumerate(posts.split("~-*-~"), 1):
        # Create a frame to contain both the bold label and the normal label
        post_frame = tk.Frame(scrollable_frame)

        post_label = tk.Label(post_frame, text=f"Post {i}:", font=('Helvetica', 14, 'bold'))
        post_label.pack(side='left')  # Align it to the left within the frame

        # Create a label for the actual post content with regular font
        content_label = tk.Label(post_frame, text=f" {post.strip()}", wraplength=600, font=('Helvetica', 14))
        content_label.pack(side='left')  # Align it to the left within the frame

        # Pack the post frame to the scrollable frame
        post_frame.pack(padx=10, pady=5, anchor='w')

def generate_post(prompt):
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        temperature=0.0,
        messages=[
            {"role": "user", "content": f"{prompt}"}
        ]
    )
    return message.content[0].text


def generate_prompt(reply, informality_percentage, topic=None, persona=None, content=None):
    # Base prompt with dynamic sections initialized as empty strings
    introduction_text = """
        [BEGIN INTRODUCTION]
        Your job is to generate social media posts, similar to what one would find on Reddit or Twitter.
        These posts are either standalone or replies to other user's posts, which will be specified in the prompt.
        You will be given a topic, a persona, and content specifications for each post. You will generate ten posts in total.
        [END INTRODUCTION]        
        """

    mimic_text = f"""
        [BEGIN MIMIC]
        Your posts are designed to mimic how a person would talk on social media. This section will go over a list of rules to follow when creating your posts. 

        1. In your posts, do not use hashtags and do not use emojis.
        2. The posts you generate should include a mix of general statements and personal opinions on the topic I give you. 
        3. Your example posts should also include personal stories, anecdotes, talks about conversations with others, or connections to other outside events. 
        4. Your posts should not have an accompanying username. 
        5. Your posts should vary in length from one sentence to five sentences. 
        6. Your posts, if possible, should contain specific information and not just general statements. Quotes, references to pop culture or news article titles (whether real or not), occupational experience, educational experience, friends, family, news personalities, elected officials, are all expected sometimes, but not all of the time. 
        7. Your posts do not need to be all directly related to the topic at hand, expressing approval or disapproval. 
        8. They can be about specific related topics. For instance, if I ask about the Superbowl against the Eagles and Patriots, you are free to make posts regarding Nick Foles or Tom Brady, even though those are not directly the game itself. 
        9. In your responses, do not use the popcorn emoji or tell people to “stay tuned” as if you are anticipating a major event. 

        Alongside these rules are what we consider to be “informality” rules, designed to mimic how people talk on social media. Based on the following percentage, you will abide by these rules. For instance, if the number is 0%, you will ignore all of these rules. If the number is 50%, you'll follow them halfway. Perhaps less grammar mistakes, more formal tone, but still incorporating some of the suggestions. If 100%, then the message will follow the informality rules to a tee. This will be known as your “informality percentage.”

        Your formality percentage is {informality_percentage}. 

        Here are the young speak rules:

        1. Posts you will generate are not one hundred percent grammatically correct. 
        2. Sometimes they should be missing capitalization and punctuation.
        3. Sometimes, to emphasize a word, it will be in all capitals like “THIS.” 
        4. Sometimes, difficult to spell words will be spelled incorrectly or a space will be forgotten between two words. 
        5. Sometimes, your posts may contain typos. 
        7. Most of the time, if an apostrophe is necessary in a contraction like “I'd” or “you'll”, your generated posts will remove it and instead use “Id” or “youll.” 
        8. In your posts, use some slang and acronyms, but do not overdo it to the point where it becomes unrealistic. 
        [END MIMIC]
        """

    # Determine if this is a reply or a standalone post and set the topic/reply text accordingly
    if reply:
        topic_text = f"""
        [BEGIN TOPIC]
        You will write a reply to the following post: {topic}
        [END TOPIC]
        """
    else:
        topic_text = f"You will write posts on the following topic: {topic}"

    # Include persona details if provided
    persona_text = f"""
        [BEGIN PERSONA]
        Here are the details of your persona: {persona}
        [END PERSONA]
        """ if persona else ""

    # Include content specifications if provided
    content_text = ""
    if content:
        content_text = f"""
            [BEGIN CONTENT]
            Here are the specifications regarding the content of your post: {content}
            [END CONTENT]
            """ if content else ""


    # Combine all the parts into the final prompt
    full_prompt = f"""
        {introduction_text}
        {mimic_text}
        {topic_text}
        {persona_text}
        {content_text}
        Now, repeat this process ten times. At the end of this, you should be returning a list of ten social media posts, nothing more. The return format should be exclusively the post, followed by this string on an empty line "~-*-~" and then the next post. So, for instance, if you were to return two posts, the return would look like this:
        Post 1
        ~-*-~
        Post 2
        
        DO NOT UNDER ANY CIRCUMSTANCE INCLUDE ANY OTHER TEXT BESIDES THE POSTS AND THE "~-*-~" SEPARATOR. NO NUMBERING THE POSTS, NO EXPLANATIONS, NOTHING. JUST THE POSTS AND THE SEPARATOR.
        """
    return full_prompt

def extract_post_id(url):
    # Regular expression to match the post ID in Reddit URLs
    pattern = r"reddit\.com\/r\/\w+\/comments\/(\w+)|redd\.it\/(\w+)"
    match = re.search(pattern, url)

    if match:
        # Return the first group that matches (handles both URL patterns)
        return match.group(1) if match.group(1) else match.group(2)
    else:
        return None

def process_post(post_id):
    post = reddit.submission(id=post_id)
    return "TITLE:" + post.title + "\n\n" + "CONTENT:" + post.selftext

if __name__ == '__main__':
    gui()
