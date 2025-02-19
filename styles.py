#styles.py
CUSTOM_CSS = """
    <style>
        /* 전체 배경 */
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
            font-family: 'Arial', sans-serif;
            background: #ECEFF1; /* 밝은 회색 배경 */
            color: #333;
            padding: 2rem;
            border-radius: 1rem;
        }

        /* 메시지 공통 스타일 */
        .chat-message {
            padding: 1.5rem;
            border-radius: 1.5rem;
            margin-bottom: 1.2rem;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(12px);
            transition: transform 0.3s ease-in-out, opacity 0.4s;
            opacity: 0;
            transform: translateY(10px);
            animation: fadeIn 0.5s forwards;
            color: white;
            position: relative;
            padding-top: 2.5rem; /* 라벨 공간 확보 */
        }

        /* USER 메시지 (스피어민트 + 딥블루) */
        .user-message {
            align-self: flex-start;
            background: linear-gradient(135deg, #2EC4B6, #011F4B);
            border-radius: 1.5rem 1.5rem 1.5rem 0;
            box-shadow: 0 4px 10px rgba(46, 196, 182, 0.3);
        }

        /* AI 메시지 (딥 블루-바이올렛) */
        .assistant-message {
            align-self: flex-end;
            background: linear-gradient(135deg, #3a1c71, #ffafbd);
            border-radius: 1.5rem 1.5rem 0 1.5rem;
            box-shadow: 0 4px 10px rgba(58, 28, 113, 0.3);
        }

        /* 메시지 라벨 (USER / AI) */
        .chat-label {
            position: absolute;
            top: 8px;
            left: 15px;
            font-size: 0.9rem;
            font-weight: bold;
            opacity: 0.8;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .user-message .chat-label {
            color: #E0F2F1;
        }

        .assistant-message .chat-label {
            color: #ffebee;
        }

        /* 메시지 내용 */
        .message-content {
            margin-top: 0.5rem;
            line-height: 1.6;
            font-size: 1.1rem;
            font-weight: 500;
        }

        /* 타임스탬프 */
        .message-timestamp {
            font-size: 0.85rem;
            opacity: 0.8;
            margin-top: 0.3rem;
            text-align: right;
            font-weight: 500;
            color: #666;
        }

        .assistant-message .message-timestamp {
            color: #ddd;
        }

        .user-message .message-timestamp {
            color: #555;
        }

        /* 메시지 입력창 */
        .stTextInput > div {
            background: white !important;
            color: black !important;
            border: 1px solid #ccc !important;
            border-radius: 8px !important;
            padding: 10px !important;
        }

        /* 헤더 */
        .main-header {
            text-align: center;
            padding: 3rem 0;
            background: linear-gradient(135deg, #3a1c71, #ffafbd);
            color: white;
            font-size: 2.2rem;
            font-weight: bold;
            border-radius: 1rem;
            margin-bottom: 2rem;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
        }

        /* 부드러운 등장 애니메이션 */
        @keyframes fadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
"""
