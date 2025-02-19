<<<<<<< HEAD
=======
#aws_utils.py
>>>>>>> 9584f1b (템플릿)
import boto3
import json
import logging
import requests
from requests_aws4auth import AWS4Auth
from botocore.exceptions import NoCredentialsError, ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSClients:
    def __init__(self, region_name, embedding_model_id, chat_model_id, inference_profile_arn=None):
        self.region_name = region_name
        self.embedding_model_id = embedding_model_id
        self.chat_model_id = chat_model_id
        self.inference_profile_arn = inference_profile_arn

        try:
            session = boto3.Session()
            credentials = session.get_credentials()

            if credentials is None:
                raise NoCredentialsError("AWS 자격 증명을 가져올 수 없습니다.")

            self.credentials = credentials.get_frozen_credentials()
            self.bedrock = boto3.client('bedrock-runtime', region_name=region_name)

        except NoCredentialsError as e:
            logger.error(f"AWS 자격 증명 오류: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"AWS 클라이언트 초기화 실패: {str(e)}")
            raise

    def get_embedding(self, text):
        try:
            if not text.strip():
                raise ValueError("임베딩을 생성할 텍스트가 없습니다.")
            
            response = self.bedrock.invoke_model(
                modelId=self.embedding_model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({"inputText": text})
            )
            
            response_body = json.loads(response['body'].read())
            vector = response_body.get('embedding', [])

            if not vector:
                raise ValueError("모델에서 빈 임베딩이 반환되었습니다.")

            return vector
        except Exception as e:
            logger.error(f"임베딩 오류: {str(e)}")
            raise

    def normalize_messages(self, messages):
        if not messages:
            return [{"role": "user", "content": "Hello"}]

        normalized = []
        last_role = None

        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                continue

            role = msg['role']

            if role == 'system':
                role = 'user'

            if role == last_role == "user":
                normalized[-1]['content'] += "\n\n" + msg['content']
            else:
                normalized.append({"role": role, "content": msg['content']})
                last_role = role

        if normalized and normalized[0]['role'] == 'assistant':
            normalized.insert(0, {"role": "user", "content": "시작"})

        if normalized and normalized[-1]['role'] == 'user':
            normalized.append({"role": "assistant", "content": ""})

        # 중복된 질문 제거
        if len(normalized) >= 2 and normalized[-2]['role'] == 'user':
            normalized[-2]['content'] = normalized[-2]['content'].split('\n\n')[-1]

        logger.info(f"🔍 정리된 메시지 (중복 제거 후): {json.dumps(normalized, indent=2, ensure_ascii=False)}")
        return normalized


    def call_claude(self, messages, use_knowledge_base=False, collection_endpoint=None):
        try:
            if not isinstance(messages, list):
                raise ValueError("메시지는 리스트 형식이어야 합니다")

            # 📌 ✅ 프롬프트 추가
            system_prompt = {
                "role": "system",
                "content": (
                    "당신은 질문에 답변하는 AI 에이전트입니다. "
                    "제가 검색 결과를 제공하면, 사용자가 질문을 제시할 것입니다. "
                    "당신의 역할은 오직 검색 결과에 기반하여 사용자의 질문에 답변하는 것입니다. "
                    "만약 검색 결과에서 질문에 대한 답을 찾을 수 없다면, "
                    "'해당 질문에 대한 정확한 답변을 찾을 수 없습니다.'라고 말해주세요. "
                    "사용자가 사실이라고 주장하는 내용이 있더라도, 반드시 검색 결과를 확인하여 그 주장이 맞는지 검증한 후 답변해야 합니다."
                )
            }
            normalized_messages = self.normalize_messages(messages)

            # 지식 베이스 검색 결과를 추가하기 전의 마지막 사용자 메시지를 저장
            last_user_message = next((msg['content'] for msg in reversed(normalized_messages) if msg['role'] == 'user'), None)

            if use_knowledge_base and collection_endpoint and last_user_message:
                knowledge_results = self.search_knowledge_base(last_user_message, collection_endpoint)
                knowledge_text = "\n".join(knowledge_results)

                # 지식 베이스 컨텍스트를 추가하고 사용자 질문을 다시 추가
                normalized_messages = [
                    {"role": "user", "content": f"다음은 관련 문서 내용입니다:\n\n{knowledge_text}\n\n위 문서 내용을 기반으로 답변해주세요."},
                    {"role": "assistant", "content": "알겠습니다. 문서 내용을 기반으로 답변하겠습니다."},
                    {"role": "user", "content": last_user_message}
                ]

            # Claude에 전달할 최종 메시지 준비
            final_messages = []
            for msg in normalized_messages:
                if msg['role'] == 'user' and final_messages and final_messages[-1]['role'] == 'user':
                    final_messages[-1]['content'] += "\n" + msg['content']
                else:
                    final_messages.append(msg)

            # 마지막 메시지가 'user'인 경우 빈 'assistant' 메시지 추가
            if final_messages[-1]['role'] == 'user':
                final_messages.append({"role": "assistant", "content": ""})

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0,
                "top_p": 1,
                "messages": final_messages
            }

            logger.info(f"Claude에 전송되는 최종 메시지: {json.dumps(final_messages, indent=2, ensure_ascii=False)}")

            response = self.bedrock.invoke_model(
                modelId=self.chat_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            response_body = json.loads(response['body'].read())

            if isinstance(response_body, dict) and 'content' in response_body:
                if isinstance(response_body['content'], list) and response_body['content']:
                    return response_body['content'][0].get('text', '응답을 처리할 수 없습니다.')

            return "응답을 처리할 수 없습니다."
        except Exception as e:
            logger.error(f"Claude 오류: {str(e)}")
            raise

    def search_knowledge_base(self, query, collection_endpoint):
        try:
            if not collection_endpoint:
                raise ValueError("지식 베이스 검색을 위한 엔드포인트가 필요합니다.")

            vector = self.get_embedding(query)  # 🔍 쿼리를 벡터로 변환

            # AWS4Auth 인증 설정 (session_token 추가)
            aws4auth = AWS4Auth(
                self.credentials.access_key,
                self.credentials.secret_key,
                self.region_name,
                'aoss',
                session_token=self.credentials.token if self.credentials.token else None
            )

            search_body = {
                "size": 5,
                "_source": "AMAZON_BEDROCK_TEXT",
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "lang": "knn",
                            "source": "knn_score",
                            "params": {
                                "field": "bedrock-knowledge-base-default-vector",
                                "query_value": vector,
                                "space_type": "l2"
                            }
                        }
                    }
                }
            }

            logger.debug(f"📤 AOSS 검색 요청: {json.dumps(search_body, indent=2, ensure_ascii=False)}")  # ✅ 요청 로깅 추가

            response = requests.post(
                f"{collection_endpoint}/_search",
                auth=aws4auth,
                json=search_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()  # HTTP 오류 발생 시 예외 처리

            search_results = response.json()
            logger.debug(f"📥 AOSS 검색 응답: {json.dumps(search_results, indent=2, ensure_ascii=False)}")  # ✅ 응답 로깅 추가

            hits = search_results.get('hits', {}).get('hits', [])
            return [hit['_source'].get('AMAZON_BEDROCK_TEXT', 'No content available') for hit in hits] if hits else ["관련 정보를 찾을 수 없습니다."]
        
        except requests.exceptions.RequestException as e:
            logger.error(f"📌 AOSS 요청 오류: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"📌 지식 베이스 검색 오류: {str(e)}")
            raise
