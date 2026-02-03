"""
Vision service for image processing (Optional)

Handles loading and initializing the vision model for image understanding.
Vision is optional for VoiceClaw - core functionality is STT → LLM → TTS.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import transformers vision components
VISION_AVAILABLE = False
try:
    from transformers import AutoProcessor, AutoModelForVision2Seq
    VISION_AVAILABLE = True
except ImportError:
    logger.warning("Vision model components not available. Vision features disabled.")


class VisionService:
    """
    Service for processing images with vision models.
    Optional feature - can be disabled without affecting core voice functionality.
    """
    
    def __init__(self):
        """Initialize the service with empty model references."""
        self.processor = None
        self.model = None
        self.initialized = False
        self.model_name = "HuggingFaceTB/SmolVLM-256M-Instruct"
        self.default_prompt = "Describe this image in detail."
        self.device = None
    
    def initialize(self):
        """
        Initialize the model, downloading it if necessary.
        
        Returns:
            bool: Whether initialization was successful
        """
        if not VISION_AVAILABLE:
            logger.info("Vision service disabled (transformers vision components not available)")
            return False
            
        if self.initialized:
            logger.info("Vision model already initialized")
            return True
        
        try:
            import torch
            
            # Determine device
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device for vision model: {self.device}")
            
            logger.info(f"Loading vision model {self.model_name}...")
            
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
            ).to(self.device)
            
            self.initialized = True
            logger.info("Vision model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vision model: {e}")
            self.initialized = False
            return False
    
    def is_ready(self) -> bool:
        """Check if the vision service is ready."""
        return self.initialized
    
    def process_image(self, image_base64: str, prompt: str = None) -> str:
        """
        Process an image and return a description.
        
        Args:
            image_base64: Base64-encoded image data
            prompt: Custom prompt for the vision model
            
        Returns:
            str: Description of the image, or error message if vision unavailable
        """
        if not self.initialized:
            return "[Vision processing unavailable]"
        
        try:
            import base64
            from io import BytesIO
            from PIL import Image
            import torch
            
            # Clean base64 string
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            
            # Decode image
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data)).convert("RGB")
            
            # Use default prompt if none provided
            if not prompt:
                prompt = self.default_prompt
            
            # Process with model
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            input_text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs = self.processor(
                text=input_text,
                images=[image],
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    do_sample=False
                )
            
            response = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
            
            # Extract assistant response
            if "Assistant:" in response:
                response = response.split("Assistant:")[-1].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return f"[Vision processing error: {str(e)}]"


# Global singleton instance
vision_service = VisionService()
