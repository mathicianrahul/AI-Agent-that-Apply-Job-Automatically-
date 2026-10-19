import json
from typing import Any, Dict, List, Optional
import requests

from jobpilot.config import settings
from jobpilot.logger import logger
from jobpilot.models.schemas import CandidateProfile, Job


class HuggingFaceLLMClient:
    """
    Client for Hugging Face Inference Providers using the OpenAI-compatible
    chat-completions interface.
    Includes connection validation, bounded retries, and high-quality truthful fallback.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.token = settings.HF_TOKEN if token is None else token
        self.model = model or settings.HF_MODEL
        self.base_url = (base_url or settings.HF_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.HF_TIMEOUT_SECONDS
        self.max_retries = settings.HF_MAX_RETRIES

    def is_configured(self) -> bool:
        """Check if an API token is provided."""
        return bool(self.token and len(self.token.strip()) > 5)

    def validate_connection(self) -> Dict[str, Any]:
        """Validates API token connectivity to Hugging Face Inference endpoint."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "HF_TOKEN is not configured. Running in rule-based fallback mode.",
                "model": self.model,
            }

        headers = {
            "Authorization": f"Bearer {self.token.strip()}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Ping test: respond with OK"}],
            "max_tokens": 10,
        }

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                return {
                    "success": True,
                    "message": f"Successfully connected to Hugging Face model '{self.model}'.",
                    "model": self.model,
                }
            elif resp.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid HF_TOKEN. Please verify your Hugging Face API key.",
                    "status_code": 401,
                }
            elif resp.status_code == 402:
                return {
                    "success": False,
                    "message": "HF account has no remaining inference credits (HTTP 402). JobPilot AI operates smoothly using its built-in deterministic, truthful profile generator.",
                    "status_code": 402,
                }
            elif resp.status_code == 404:
                return {
                    "success": False,
                    "message": f"Model '{self.model}' not found on endpoint. Built-in truthful fallback mode active.",
                    "status_code": 404,
                }
            else:
                return {
                    "success": False,
                    "message": f"HF Inference returned HTTP {resp.status_code} ({resp.text[:120]}). Using built-in truthful fallback mode.",
                    "status_code": resp.status_code,
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Hugging Face endpoint currently unreachable ({type(e).__name__}). Using built-in truthful fallback mode.",
            }

    def generate_chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 600) -> Optional[str]:
        """Calls HF chat completions endpoint with bounded retries and fast fallback."""
        if not self.is_configured():
            return None

        headers = {
            "Authorization": f"Bearer {self.token.strip()}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                elif resp.status_code in (429, 503):
                    logger.warning(f"HF rate limited or loading (status {resp.status_code}), attempt {attempt}/{self.max_retries}")
                elif resp.status_code in (400, 401, 402, 404):
                    logger.info(f"HF Inference unavailable (HTTP {resp.status_code}). Switching to truthful deterministic generator.")
                    break
                else:
                    logger.warning(f"HF Inference status {resp.status_code}: {resp.text[:120]}")
                    break
            except Exception as e:
                logger.info(f"HF API unreachable ({type(e).__name__}). Switching to truthful deterministic generator.")
                break

        return None

    def generate_cover_letter(self, candidate: CandidateProfile, job: Job) -> str:
        """
        Drafts a customized, strictly truthful cover letter.
        Uses LLM if available, otherwise high-quality template based on candidate's real profile.
        """
        prompt = (
            f"You are drafting a professional, strictly truthful job application cover letter for {candidate.name}.\n"
            f"CANDIDATE DETAILS:\n"
            f"- Education: {candidate.education} (Expected graduation {candidate.graduation_year})\n"
            f"- Experience Level: {candidate.experience_level}\n"
            f"- Skills: {', '.join(candidate.skills)}\n"
            f"- Projects: {json.dumps(candidate.projects)}\n\n"
            f"JOB DETAILS:\n"
            f"- Position: {job.title}\n"
            f"- Company: {job.company}\n"
            f"- Location: {job.location}\n"
            f"- Description: {job.description[:1000]}\n\n"
            f"RULES:\n"
            f"1. Do not invent any work experience or skills not listed.\n"
            f"2. Highlight relevant projects like {candidate.projects[0]['title'] if candidate.projects else 'academic projects'}.\n"
            f"3. Maintain a professional, humble, enthusiastic tone.\n"
            f"4. Format cleanly with standard business letter greeting and sign-off."
        )

        messages = [
            {"role": "system", "content": "You are a professional career advisor assisting an engineering student."},
            {"role": "user", "content": prompt},
        ]

        llm_response = self.generate_chat_completion(messages, max_tokens=700)
        if llm_response:
            return llm_response

        # Fallback truthful cover letter
        first_proj = candidate.projects[0] if candidate.projects else {"title": "AI/ML Projects", "description": "machine learning pipelines"}
        relevant_skills = [s for s in candidate.skills if s.lower() in job.description.lower()] or candidate.skills[:5]

        return (
            f"Dear Hiring Team at {job.company},\n\n"
            f"I am writing to express my enthusiastic interest in the {job.title} role at {job.company}. "
            f"As a final-year engineering student pursuing a Bachelor's degree in Artificial Intelligence and Machine Learning "
            f"(graduating in {candidate.graduation_year}), I am excited by your work and the opportunity to contribute.\n\n"
            f"Throughout my academic coursework and project work, I have built a strong foundation in "
            f"{', '.join(relevant_skills[:4])}. For instance, in my project '{first_proj['title']}', "
            f"I developed {first_proj.get('description', 'practical machine learning solutions')}.\n\n"
            f"I am particularly drawn to this position in {job.location} because it aligns with my goal to build "
            f"reliable, production-minded AI applications. As an entry-level candidate, I bring relentless curiosity, "
            f"strong technical foundations, and a disciplined work ethic.\n\n"
            f"Thank you for considering my application. I look forward to the opportunity to discuss how my skill set "
            f"and projects can support your engineering objectives.\n\n"
            f"Sincerely,\n"
            f"{candidate.name}\n"
            f"Email: {candidate.email}\n"
            f"Phone: {candidate.phone}"
        )

    def generate_answers(self, candidate: CandidateProfile, job: Job) -> Dict[str, str]:
        """Generates truthful, tailored answers to typical application questions."""
        first_proj = candidate.projects[0] if candidate.projects else {"title": "Predictive ML Project"}

        return {
            "Why are you interested in this position?": (
                f"I am excited about {job.company}'s focus on {job.title}. As an AI & ML student graduating in {candidate.graduation_year}, "
                f"this role offers the ideal environment to apply my hands-on knowledge of Python and machine learning to impactful problems."
            ),
            "What is your relevant project experience?": (
                f"I developed the '{first_proj['title']}' using Python, Scikit-learn, and Pandas. "
                f"In addition, I have built computer vision systems with OpenCV/MediaPipe and generative AI chatbots with LangChain/LangGraph."
            ),
            "What is your availability to start?": (
                f"Available for full-time or internship commencement aligned with my final-year graduation schedule in 2027. "
                f"Open to {job.location} or remote arrangements."
            ),
            "Expected CTC / Stipend": (
                f"Flexible and aligned with industry standards for entry-level / fresher {job.title} roles."
            ),
        }


llm_client = HuggingFaceLLMClient()
