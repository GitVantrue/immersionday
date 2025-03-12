#aws_utils.py
import boto3
import json
import logging
import requests
from requests_aws4auth import AWS4Auth
from botocore.exceptions import NoCredentialsError, ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSClients:
    def __init__(self, region_name, embedding_model_id, chat_model_id):
        self.region_name = region_name
        self.embedding_model_id = embedding_model_id
        self.chat_model_id = chat_model_id
        

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

        if len(normalized) >= 2 and normalized[-2]['role'] == 'user':
            normalized[-2]['content'] = normalized[-2]['content'].split('\n\n')[-1]

        logger.info(f"🔍 정리된 메시지 (중복 제거 후): {json.dumps(normalized, indent=2, ensure_ascii=False)}")
        return normalized

    def search_knowledge_base(self, query, collection_endpoint):
        try:
            if not collection_endpoint:
                return []

            vector = self.get_embedding(query)

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

            response = requests.post(
                f"{collection_endpoint}/_search",
                auth=aws4auth,
                json=search_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            search_results = response.json()
            hits = search_results.get('hits', {}).get('hits', [])
            
            if not hits:
                return []
                
            results = []
            for hit in hits:
                text = hit['_source'].get('AMAZON_BEDROCK_TEXT')
                if text and text.strip():
                    results.append(text)
            
            return results if results else []

        except Exception as e:
            logger.error(f"📌 지식 베이스 검색 오류: {str(e)}")
            return []

    def call_claude(self, messages, use_knowledge_base=False, collection_endpoint=None):
        try:
            if not isinstance(messages, list):
                raise ValueError("메시지는 리스트 형식이어야 합니다")
    
            normalized_messages = self.normalize_messages(messages)
            last_user_message = next((msg['content'] for msg in reversed(normalized_messages) if msg['role'] == 'user'), None)
    
            final_messages = []
            
            if use_knowledge_base and collection_endpoint and last_user_message:
                # 지식 기반 모드일 때 사용할 프롬프트
                kb_prompt = (
                    "모든 대답은 단계적으로 사고하여 대답합니다. "
                    "검색 결과를 찾을수 없을 시에도 일반적인 지식을 활용하여 상세한 답변을 제공해야합니다. "
                    "일반적인 대답을 제공할 시에는 '관련 문서에서 직접적인 답변을 찾을 수 없어, 일반적인 지식을 바탕으로 답변드리겠습니다:'라고 먼저 명시합니다.\n\n"
                    "일반적인 대답과 문서에서 찾아서 답변을 제공하는것을 명확하게 구분하고 대답합니다."
                )
                
                knowledge_results = self.search_knowledge_base(last_user_message, collection_endpoint)
                
                if knowledge_results:
                    knowledge_text = "\n".join(knowledge_results)
                    final_messages = [
                        {"role": "user", "content": f"{kb_prompt}다음은 관련 문서 내용입니다:\n\n{knowledge_text}\n\n위 문서 내용을 기반으로 답변해주세요:\n{last_user_message}"}
                    ]
                else:
                    final_messages = [
                        {"role": "user", "content": f"{kb_prompt}{last_user_message}"}
                    ]
            else:
                # 일반 모드일 때 사용할 프롬프트 (지식 기반 언급 제외)
                general_prompt = (
                    "모든 대답은 단계적으로 사고하여 대답합니다. "
                    "질문에 대해 상세한 답변을 제공해야합니다."
                )
                
                if normalized_messages and normalized_messages[0]['role'] == 'user':
                    normalized_messages[0]['content'] = general_prompt + "\n\n" + normalized_messages[0]['content']
                else:
                    normalized_messages.insert(0, {"role": "user", "content": general_prompt})
                final_messages = normalized_messages
    
            if final_messages[-1]['role'] == 'user':
                final_messages.append({"role": "assistant", "content": ""})
    
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0,
                "top_p": 0.8,
                "top_k": 3,
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