import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    Pinecone = None

try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class VectorService:
    """
    Vector Database Service for Hospital Protocols and Knowledge Base
    Uses Pinecone for vector storage and OpenAI/Gemini for embeddings
    """
    
    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "hospital-protocols")
        
        # Check which embedding provider to use
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Set embedding model and dimension based on provider
        if self.openai_api_key:
            self.embedding_provider = "openai"
            self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
        elif self.gemini_api_key:
            self.embedding_provider = "gemini"
            self.embedding_model = "models/embedding-001"
            self.embedding_dimension = 768  # Gemini embedding dimension
        else:
            self.embedding_provider = "mock"
            self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
        
        self.pc = None
        self.index = None
        self.openai_client = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize Pinecone and embedding clients"""
        
        logger.info("Initializing Vector Service...")
        
        # Check if Pinecone is available
        if not Pinecone:
            logger.warning("⚠️  Pinecone not installed. Vector search disabled.")
            logger.info("   Install with: pip install pinecone-client")
            self.initialized = False
            return
        
        if not self.pinecone_api_key:
            logger.warning("⚠️  PINECONE_API_KEY not found. Vector search disabled.")
            self.initialized = False
            return
        
        try:
            # Initialize Pinecone
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            
            # Check if index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.pinecone_environment
                    )
                )
                # Wait for index to be ready
                await asyncio.sleep(5)
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            
            # Initialize embedding client based on provider
            if self.embedding_provider == "openai" and openai:
                self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
                logger.info("✅ Using OpenAI embeddings")
            elif self.embedding_provider == "gemini" and genai:
                genai.configure(api_key=self.gemini_api_key)
                logger.info("✅ Using Gemini embeddings")
            else:
                logger.warning("⚠️  No embedding API available. Using mock embeddings.")
                logger.info("   Install: pip install google-generativeai (for Gemini)")
                logger.info("   Or add OPENAI_API_KEY to .env (for OpenAI)")
            
            self.initialized = True
            logger.info(f"✅ Vector Service initialized with index: {self.index_name}")
            logger.info(f"   Embedding provider: {self.embedding_provider}")
            logger.info(f"   Embedding dimension: {self.embedding_dimension}")
            
            # Get index stats
            stats = self.index.describe_index_stats()
            logger.info(f"   Index vectors: {stats.get('total_vector_count', 0)}")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vector Service: {e}")
            self.initialized = False
    
    async def health_check(self) -> bool:
        """Check if vector service is healthy"""
        if not self.initialized:
            return False
        
        try:
            if self.index:
                self.index.describe_index_stats()
                return True
            return False
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return False
    
    async def close(self):
        """Cleanup resources"""
        logger.info("Closing Vector Service...")
        self.initialized = False
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        Uses OpenAI, Gemini, or falls back to mock embeddings
        """
        
        if not self.initialized:
            return self._generate_mock_embedding()
        
        try:
            # Use OpenAI embeddings
            if self.embedding_provider == "openai" and self.openai_client:
                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
            
            # Use Gemini embeddings
            elif self.embedding_provider == "gemini" and genai:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            
            # Fallback to mock embeddings
            else:
                logger.warning("Using mock embeddings (no API available)")
                return self._generate_mock_embedding()
        
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            logger.warning("Falling back to mock embeddings")
            return self._generate_mock_embedding()
    
    def _generate_mock_embedding(self) -> List[float]:
        """Generate a mock embedding vector for testing"""
        import random
        random.seed(42)  # Consistent mock embeddings
        return [random.random() for _ in range(self.embedding_dimension)]
    
    async def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Insert or update a document in the vector database
        
        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Additional metadata (category, source, etc.)
        
        Returns:
            True if successful
        """
        
        if not self.initialized:
            logger.warning("Vector service not initialized. Document not stored.")
            return False
        
        try:
            # Generate embedding
            embedding = await self.generate_embedding(text)
            
            # Prepare metadata
            full_metadata = {
                "text": text[:1000],  # Store first 1000 chars for reference
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # Upsert to Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": doc_id,
                        "values": embedding,
                        "metadata": full_metadata
                    }
                ]
            )
            
            logger.info(f"✅ Document upserted: {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to upsert document {doc_id}: {e}")
            return False
    
    async def upsert_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert multiple documents
        
        Args:
            documents: List of dicts with 'id', 'text', and optional 'metadata'
        
        Returns:
            Number of successfully inserted documents
        """
        
        if not self.initialized:
            logger.warning("Vector service not initialized. Batch not stored.")
            return 0
        
        success_count = 0
        vectors = []
        
        try:
            # Generate embeddings for all documents
            for doc in documents:
                doc_id = doc["id"]
                text = doc["text"]
                metadata = doc.get("metadata", {})
                
                embedding = await self.generate_embedding(text)
                
                full_metadata = {
                    "text": text[:1000],
                    "timestamp": datetime.now().isoformat(),
                    **metadata
                }
                
                vectors.append({
                    "id": doc_id,
                    "values": embedding,
                    "metadata": full_metadata
                })
            
            # Batch upsert
            if vectors:
                self.index.upsert(vectors=vectors)
                success_count = len(vectors)
                logger.info(f"✅ Batch upserted: {success_count} documents")
        
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
        
        return success_count
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filter_metadata: Filter results by metadata (e.g., {"category": "protocol"})
        
        Returns:
            List of matching documents with scores
        """
        
        if not self.initialized:
            logger.warning("Vector service not initialized. Returning empty results.")
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_metadata
            )
            
            # Format results
            matches = []
            for match in results.get("matches", []):
                matches.append({
                    "id": match["id"],
                    "score": match["score"],
                    "text": match["metadata"].get("text", ""),
                    "metadata": {
                        k: v for k, v in match["metadata"].items()
                        if k not in ["text", "timestamp"]
                    },
                    "timestamp": match["metadata"].get("timestamp")
                })
            
            logger.info(f"Found {len(matches)} matches for query")
            return matches
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_protocols(
     self,
     query: str,
     protocol_type: Optional[str] = None,
     top_k: int = 3,
     filters: Optional[Dict[str, Any]] = None
     ) ->  List[Dict[str, Any]]:
     """
    Search for hospital protocols
    
    Args:
        query: Search query
        protocol_type: Filter by protocol type (e.g., "emergency", "surgery")
        top_k: Number of results
        filters: Additional metadata filters
    
    Returns:
        List of matching protocols
     """
    
     filter_metadata = {"category": "protocol"}
    
    # Add protocol_type filter if provided
     if protocol_type:
        filter_metadata["type"] = protocol_type
    
    # Add additional filters if provided
     if filters:
        filter_metadata.update(filters)
    
     return await self.search(query, top_k, filter_metadata)

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector database"""
        
        if not self.initialized:
            return False
        
        try:
            self.index.delete(ids=[doc_id])
            logger.info(f"✅ Document deleted: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    async def delete_all(self, namespace: Optional[str] = None) -> bool:
        """Delete all documents (use with caution!)"""
        
        if not self.initialized:
            return False
        
        try:
            self.index.delete(delete_all=True, namespace=namespace or "")
            logger.warning("⚠️  All documents deleted from index")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all documents: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        
        if not self.initialized:
            return {"error": "Vector service not initialized"}
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", self.embedding_dimension),
                "index_fullness": stats.get("index_fullness", 0),
                "namespaces": stats.get("namespaces", {}),
                "embedding_provider": self.embedding_provider,
                "initialized": True
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Example usage for seeding protocols
async def seed_hospital_protocols(vector_service: VectorService):
    """
    Example function to seed the vector database with hospital protocols
    Run this once to populate your knowledge base
    """
    
    protocols = [
        {
            "id": "protocol_001",
            "text": """
            Emergency Triage Protocol:
            1. Assess patient vital signs immediately
            2. Categorize based on severity (Red: Critical, Yellow: Urgent, Green: Non-urgent)
            3. Critical patients get immediate attention
            4. Document all observations
            5. Notify appropriate specialists
            """,
            "metadata": {
                "category": "protocol",
                "type": "emergency",
                "title": "Emergency Triage Protocol"
            }
        },
        {
            "id": "protocol_002",
            "text": """
            Infection Control Protocol:
            1. Use appropriate PPE for all patient interactions
            2. Hand hygiene before and after patient contact
            3. Isolate infectious patients
            4. Follow standard precautions
            5. Regular equipment sterilization
            """,
            "metadata": {
                "category": "protocol",
                "type": "infection_control",
                "title": "Infection Control Protocol"
            }
        },
        {
            "id": "protocol_003",
            "text": """
            Patient Admission Protocol:
            1. Verify patient identity and insurance
            2. Complete admission paperwork
            3. Assign bed based on condition and availability
            4. Initial patient assessment by nurse
            5. Physician consultation within 2 hours
            6. Update hospital management system
            """,
            "metadata": {
                "category": "protocol",
                "type": "admission",
                "title": "Patient Admission Protocol"
            }
        }
    ]
    
    count = await vector_service.upsert_batch(protocols)
    logger.info(f"Seeded {count} protocols into vector database")
    return count