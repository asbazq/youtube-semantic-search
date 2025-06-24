
python -m scripts.fetch_captions




mysql -u root -p


python -m db.insert_chunks

us-east- 1


http://localhost:8000/health

http://localhost:8000/docs#/default/search_search_post --- main link

http://localhost:8000/redoc

http://localhost:8000/openapi.json






PS E:\Semantic Search Engine> python -m run_pipeline
🔁 Starting Full Pipeline for YouTube Semantic Search
🎥 Enter the YouTube video ID: c36lUUr864M
📝 Enter a title/label for the video: PyTorch - Deep Learning

🎬 Starting pipeline for: PyTorch - Deep Learning (c36lUUr864M)

🚀 Running: E:\Semantic Search Engine\.venv\Scripts\python.exe scripts/fetch_captions.py c36lUUr864M PyTorch - Deep Learning
2025-06-21 00:30:04,482 | INFO | 🎬 Processing 1 video: PyTorch - Deep Learning (c36lUUr864M)
2025-06-21 00:30:04,482 | INFO | 🔄 Fetching transcript for PyTorch - Deep Learning (c36lUUr864M) using yt-dlp...
2025-06-21 00:30:14,648 | INFO | ✅ Saved captions for PyTorch - Deep Learning (c36lUUr864M) - 5973 segments
2025-06-21 00:30:14,651 | INFO | 🎯 Completed! Successfully processed 1/1 videos
✅ E:\Semantic Search Engine\.venv\Scripts\python.exe scripts/fetch_captions.py c36lUUr864M PyTorch - Deep Learning completed successfully


🚀 Running: E:\Semantic Search Engine\.venv\Scripts\python.exe scripts/preprocess_captions.py
🔍 Found 1 caption files
🆕 Processing new file: PyTorch - Deep Learning_c36lUUr864M.json
🔄 Processing data\captions\PyTorch - Deep Learning_c36lUUr864M.json...
📥 Loaded 5973 caption segments
🔗 Combined into 5417 blocks
✂️ Split into 5417 manageable blocks
📝 Created 1544 semantic chunks
✅ Saved processed chunks to data\chunks\processed_PyTorch - Deep Learning_c36lUUr864M.json

🎯 Chunk Statistics:
Total chunks: 1544
Word count - Min: 3, Max: 34, Avg: 22.0
Duration - Min: 0.5s, Max: 20.7s, Avg: 8.1s

📋 First 3 chunks:

--- Chunk 1 ---
Time: 1.9s - 6.9s (5.0s)
Words: 20
Text: Welcome guys to this all-in-one pie. Torch video this video takes all parts. From my beginner pie torch playlist and.

--- Chunk 2 ---
Time: 8.5s - 12.7s (4.3s)
Words: 18
Text: Combines it into one single video. The course goes from zero to. Intermediate level and teaches you all.

--- Chunk 3 ---
Time: 14.3s - 19.2s (4.9s)
Words: 21
Text: The fundamentals you have to know to be. Confident with this deep learning framework. I will leave timestamps for each section.

🎉 Processing complete! Processed 0 files.
✅ E:\Semantic Search Engine\.venv\Scripts\python.exe scripts/preprocess_captions.py completed successfully


🚀 Running: E:\Semantic Search Engine\.venv\Scripts\python.exe scripts/embed_chunks.py
2025-06-21 00:30:29,671 | INFO | 📦 Loading embedding model: all-mpnet-base-v2
2025-06-21 00:30:29,676 | INFO | Use pytorch device_name: cpu
2025-06-21 00:30:29,676 | INFO | Load pretrained SentenceTransformer: all-mpnet-base-v2
2025-06-21 00:30:36,028 | INFO | ✅ Model loaded successfully
2025-06-21 00:30:36,030 | INFO | 🚀 Found 1 chunk files to process
2025-06-21 00:30:36,030 | INFO | 🔄 Embedding: processed_PyTorch - Deep Learning_c36lUUr864M.json
Batches: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 49/49 [01:53<00:00,  2.31s/it]
2025-06-21 00:32:31,397 | INFO | ✅ Saved embeddings to: processed_PyTorch - Deep Learning_c36lUUr864M.json
2025-06-21 00:32:31,413 | INFO | 
🎯 Embedding Summary:
2025-06-21 00:32:31,413 | INFO | 🆕 Embedded files: 1
2025-06-21 00:32:31,414 | INFO | ⏭️ Skipped files : 0
2025-06-21 00:32:31,414 | INFO | ✅ Embedding complete!
✅ E:\Semantic Search Engine\.venv\Scripts\python.exe scripts/embed_chunks.py completed successfully

2025-06-21 00:32:32,902 | INFO | 🔐 Loaded environment from: E:\Semantic Search Engine\.env
🔗 Testing Pinecone connection...
2025-06-21 00:32:32,904 | INFO | ✅ Pinecone client initialized
2025-06-21 00:32:34,101 | INFO | 📦 Index 'youtube-semantic-search' already exists
2025-06-21 00:32:36,504 | INFO | 📊 7547 vectors in index
✅ Pinecone index is accessible. Status: 7547 vectors present.


🚀 Running: E:\Semantic Search Engine\.venv\Scripts\python.exe db/upload_embeddings.py
2025-06-21 00:32:37,292 | INFO | 🔐 Loaded environment from: E:\Semantic Search Engine\.env
2025-06-21 00:32:37,299 | INFO | ✅ Pinecone client initialized
2025-06-21 00:32:38,189 | INFO | 📦 Index 'youtube-semantic-search' already exists
2025-06-21 00:32:40,167 | INFO | 📊 7547 vectors in index
2025-06-21 00:32:40,168 | INFO | 🚀 Found 1 embedding files to upload
2025-06-21 00:32:40,442 | INFO | 📊 Current index has 7547 vectors in namespace 'youtube-semantic-search'
2025-06-21 00:32:40,445 | INFO | 🔄 Processing processed_PyTorch - Deep Learning_c36lUUr864M.json...
2025-06-21 00:32:43,623 | INFO | ✅ Uploaded batch 1: 100 vectors
2025-06-21 00:32:44,673 | INFO | ✅ Uploaded batch 2: 100 vectors
2025-06-21 00:32:45,742 | INFO | ✅ Uploaded batch 3: 100 vectors
2025-06-21 00:32:46,762 | INFO | ✅ Uploaded batch 4: 100 vectors
2025-06-21 00:32:47,781 | INFO | ✅ Uploaded batch 5: 100 vectors
2025-06-21 00:32:48,782 | INFO | ✅ Uploaded batch 6: 100 vectors
2025-06-21 00:32:49,891 | INFO | ✅ Uploaded batch 7: 100 vectors
2025-06-21 00:32:50,930 | INFO | ✅ Uploaded batch 8: 100 vectors
2025-06-21 00:32:52,011 | INFO | ✅ Uploaded batch 9: 100 vectors
2025-06-21 00:32:53,401 | INFO | ✅ Uploaded batch 10: 100 vectors
2025-06-21 00:32:54,531 | INFO | ✅ Uploaded batch 11: 100 vectors
2025-06-21 00:32:55,579 | INFO | ✅ Uploaded batch 12: 100 vectors
2025-06-21 00:32:56,840 | INFO | ✅ Uploaded batch 13: 100 vectors
2025-06-21 00:32:58,098 | INFO | ✅ Uploaded batch 14: 100 vectors
2025-06-21 00:32:59,368 | INFO | ✅ Uploaded batch 15: 100 vectors
2025-06-21 00:33:00,067 | INFO | ✅ Uploaded batch 16: 44 vectors
2025-06-21 00:33:00,067 | INFO | 🎯 Completed processed_PyTorch - Deep Learning_c36lUUr864M.json: 1544/1544 vectors uploaded
2025-06-21 00:33:00,356 | INFO | 🎉 Upload complete!
2025-06-21 00:33:00,357 | INFO | 📊 Vectors uploaded this session: 1544
2025-06-21 00:33:00,357 | INFO | 📊 Total vectors in index: 7547
2025-06-21 00:33:00,358 | INFO | 📊 Net increase: 0
✅ E:\Semantic Search Engine\.venv\Scripts\python.exe db/upload_embeddings.py completed successfully

🎉 Pipeline completed for video!

🚀 Running: E:\Semantic Search Engine\.venv\Scripts\python.exe search/semantic_search.py
2025-06-21 00:33:12,656 | INFO | 🔐 Loaded environment from: E:\Semantic Search Engine\.env
2025-06-21 00:33:12,658 | INFO | 🔄 Initializing YouTube Semantic Search...
2025-06-21 00:33:12,658 | INFO | 📦 Loading embedding model: all-mpnet-base-v2
2025-06-21 00:33:12,662 | INFO | Use pytorch device_name: cpu
2025-06-21 00:33:12,662 | INFO | Load pretrained SentenceTransformer: all-mpnet-base-v2
2025-06-21 00:33:18,016 | INFO | ✅ Embedding model loaded
2025-06-21 00:33:18,016 | INFO | 🔗 Connecting to Pinecone...
2025-06-21 00:33:18,017 | INFO | ✅ Pinecone client initialized
2025-06-21 00:33:19,285 | INFO | 📦 Index 'youtube-semantic-search' already exists
2025-06-21 00:33:21,199 | INFO | 📊 7547 vectors in index
2025-06-21 00:33:21,200 | INFO | ✅ Pinecone connection established

🎥 Welcome to YouTube Semantic Search Engine

Options:
1. General search
2. Search by specific video
3. Show available videos
4. Exit
Choose an option (1-4): 1
🔍 Enter search query: Feed Forward neural network
Batches: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  7.14it/s]
2025-06-21 00:33:44,094 | INFO | 🔍 Searching top 10 results for: 'Feed Forward neural network'

📊 Found 10 result(s):

1. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 0:31:47 - 0:31:51
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=1907s
   📝 Text: To this particular feed forward neural network and I should be able to neural network and I should be able to neural network and I should be able to get my output let's say this specific get my output...

2. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:21:22 - 3:21:27
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=12082s
   📝 Text: Point about feed forward neural network point about feed forward neural network....

3. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 0:33:07 - 0:33:11
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=1987s
   📝 Text: My feed forward neural network this is my feed forward neural network network neural network okay and here you network neural network okay and here you network neural network okay and here you can see...

4. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 1:51:46 - 1:51:50
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=6706s
   📝 Text: Neural forward it to the feed forward neural forward it to the feed forward neural network so, for that here you can see an network so, for that here you can see an network so, for that here you can....

5. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:40:33 - 3:40:38
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=13233s
   📝 Text: Be understanding about the we'll also, be understanding about the feed forward neural network but now, if feed forward neural network but now, if feed forward neural network but now, if you see from t...

6. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:16:24 - 3:16:33
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=11784s
   📝 Text: So, so, here why feed forward neural network here why feed forward neural network again based on the research paper I will again based on the research paper I will again based on the research paper I ...

7. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:16:05 - 3:16:10
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=11765s
   📝 Text: Neural network okay this also, you really neural network okay this also, you really neural network okay this also, you really need to understand why feed forward need to understand why feed forward ne...

8. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:30:57 - 3:31:02
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=12657s
   📝 Text: This see over here we are passing this information into feed forward neural information into feed forward neural information into feed forward neural network but before network but before network but ...

9. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:18:58 - 3:19:03
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=11938s
   📝 Text: Okay obtained from the self attention okay now, how does feed forward neural network now, how does feed forward neural network now, how does feed forward neural network help this feed forward neural n...

10. 🎬 Video: Krish Naik - Transformers
   ⏰ Time: 3:17:38 - 3:17:44
   🔗 URL: https://www.youtube.com/watch?v=3bPhDUSAUYI&t=11858s
   📝 Text: Forward neural network so, what it feed forward neural network so, what it does over here I will just add one point does over here I will just add one point does over here I will just add one point....

Options:
1. General search
2. Search by specific video
3. Show available videos
4. Exit
Choose an option (1-4): 2
📼 Enter video ID: c36lUUr864M
🔍 Enter search query: Feed Forward Neural Network
Batches: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 11.19it/s]

📊 Found 10 result(s):

1. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 3:52:58 - 3:53:05
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=13978s
   📝 Text: And then, we create a simple. Feed forward neural net so, this is a. Fully connected neural network with one. Hidden layer....

2. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 2:41:16 - 2:41:25
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=9676s
   📝 Text: So, here we must implement the. Sigmoid function at the end so, let's. Have a look at our. Neural net in a binary classification. Case....

3. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 1:14:36 - 1:14:47
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=4476s
   📝 Text: Last step we do our training loop. So, this the training loop so. We start by doing our. Forward pass so, here we compute....

4. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 2:39:08 - 2:39:14
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=9548s
   📝 Text: Here so, we must not use the softmax. Layer in our neural net so, we must not. Implement this for ourselves....

5. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 4:09:46 - 4:09:50
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=14986s
   📝 Text: Look at the neural net again and we see. That we have a linear layer at the end so, these....

6. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 3:01:08 - 3:01:18
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=10868s
   📝 Text: So, let's do this so. Let's comment this out again. And now, let's create a class. Neural net and this has to be derived....

7. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 2:53:05 - 2:53:13
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=10385s
   📝 Text: Then, we will implement. Our neural net with input layer hidden. Layer and output layer. And we will also, apply actuation. Functions....

8. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 1:39:55 - 1:40:01
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=5995s
   📝 Text: Output size and the forward pass then, we create. The loss and the optimizer functions and. Then, we do the actual training loop with....

9. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 3:59:59 - 4:00:06
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=14399s
   📝 Text: So, we have the input and then, the neural. Net and now, if we do a double click. Then, we see more details....

10. 🎬 Video: PyTorch - Deep Learning
   ⏰ Time: 1:18:51 - 1:18:59
   🔗 URL: https://www.youtube.com/watch?v=c36lUUr864M&t=4731s
   📝 Text: So, this is nn.linear. And this needs an input size and an. Output size of our features. And for this we need to do some....

Options:
1. General search
2. Search by specific video
3. Show available videos
4. Exit
Choose an option (1-4):