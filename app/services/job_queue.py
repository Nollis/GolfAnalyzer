"""
Job Queue Service - Abstracts queue implementation for local/cloud deployment.

Local: Uses in-memory queue with threading
Cloud: Can be swapped for AWS SQS, Redis, or RabbitMQ
"""
import asyncio
import threading
import queue
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class QueueMessage:
    """Message in the job queue."""
    job_id: str
    user_id: str
    video_path: str
    handedness: Optional[str]
    view: str
    club_type: Optional[str]


class JobQueueBase(ABC):
    """Abstract base class for job queue implementations."""
    
    @abstractmethod
    def enqueue(self, message: QueueMessage) -> bool:
        """Add a job to the queue."""
        pass
    
    @abstractmethod
    def dequeue(self, timeout: float = 1.0) -> Optional[QueueMessage]:
        """Get next job from queue (blocking with timeout)."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get current queue size."""
        pass


class InMemoryQueue(JobQueueBase):
    """
    In-memory queue for local development.
    
    Thread-safe, suitable for single-instance deployment.
    For production, replace with SQS/Redis implementation.
    """
    
    def __init__(self, maxsize: int = 100):
        self._queue: queue.Queue[QueueMessage] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        logger.info(f"Initialized in-memory job queue (max size: {maxsize})")
    
    def enqueue(self, message: QueueMessage) -> bool:
        """Add a job to the queue."""
        try:
            self._queue.put_nowait(message)
            logger.info(f"Job {message.job_id} added to queue (size: {self._queue.qsize()})")
            return True
        except queue.Full:
            logger.error(f"Queue full, cannot add job {message.job_id}")
            return False
    
    def dequeue(self, timeout: float = 1.0) -> Optional[QueueMessage]:
        """Get next job from queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def task_done(self):
        """Mark current task as done."""
        self._queue.task_done()


class SQSQueue(JobQueueBase):
    """
    AWS SQS queue implementation (placeholder for cloud deployment).
    
    To enable:
    1. pip install boto3
    2. Set AWS_SQS_QUEUE_URL environment variable
    3. Configure AWS credentials
    """
    
    def __init__(self, queue_url: Optional[str] = None):
        self.queue_url = queue_url or os.getenv("AWS_SQS_QUEUE_URL")
        if not self.queue_url:
            raise ValueError("SQS queue URL not configured")
        
        try:
            import boto3
            self.sqs = boto3.client('sqs')
            logger.info(f"Connected to SQS queue: {self.queue_url}")
        except ImportError:
            raise RuntimeError("boto3 not installed. Run: pip install boto3")
    
    def enqueue(self, message: QueueMessage) -> bool:
        """Send message to SQS queue."""
        import json
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps({
                    "job_id": message.job_id,
                    "user_id": message.user_id,
                    "video_path": message.video_path,
                    "handedness": message.handedness,
                    "view": message.view,
                    "club_type": message.club_type,
                })
            )
            logger.info(f"Job {message.job_id} sent to SQS")
            return True
        except Exception as e:
            logger.error(f"Failed to send job to SQS: {e}")
            return False
    
    def dequeue(self, timeout: float = 20.0) -> Optional[QueueMessage]:
        """Receive message from SQS queue."""
        import json
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=int(timeout),
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return None
            
            msg = messages[0]
            body = json.loads(msg['Body'])
            
            # Delete message after receiving
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=msg['ReceiptHandle']
            )
            
            return QueueMessage(
                job_id=body["job_id"],
                user_id=body["user_id"],
                video_path=body["video_path"],
                handedness=body.get("handedness"),
                view=body["view"],
                club_type=body.get("club_type"),
            )
        except Exception as e:
            logger.error(f"Failed to receive from SQS: {e}")
            return None
    
    def size(self) -> int:
        """Get approximate queue size from SQS."""
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            return int(response['Attributes']['ApproximateNumberOfMessages'])
        except Exception:
            return -1


def get_job_queue() -> JobQueueBase:
    """
    Factory function to get the appropriate queue implementation.
    
    Uses SQS if AWS_SQS_QUEUE_URL is set, otherwise uses in-memory queue.
    """
    sqs_url = os.getenv("AWS_SQS_QUEUE_URL")
    
    if sqs_url:
        logger.info("Using AWS SQS queue")
        return SQSQueue(sqs_url)
    else:
        logger.info("Using in-memory queue (local development)")
        return InMemoryQueue()


# Global queue instance (singleton)
_job_queue: Optional[JobQueueBase] = None


def init_job_queue() -> JobQueueBase:
    """Initialize and return the global job queue."""
    global _job_queue
    if _job_queue is None:
        _job_queue = get_job_queue()
    return _job_queue


def get_queue() -> JobQueueBase:
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = init_job_queue()
    return _job_queue


