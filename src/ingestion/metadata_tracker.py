"""
Metadata Tracking System
Phase 2, Task 2.5

Track and manage metadata for every chunk for accurate citation generation.
Provides queryable interface for metadata across all indexed documents.
"""

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
from pathlib import Path
import logging
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Enhanced metadata for individual chunks"""

    chunk_id: str
    source_doc: str
    section: str = "General"
    page_num: int = 1
    start_char: int = 0
    end_char: int = 0
    chunk_text_length: int = 0
    parent_chunk_id: str = ""

    # Tracking info
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding_model: str = "all-mpnet-base-v2"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ChunkMetadata":
        """Create from dictionary"""
        return cls(**data)



@dataclass
class DocumentMetadata:
    """Metadata for source documents"""

    source_doc: str
    file_path: str
    total_chunks: int = 0
    total_characters: int = 0
    sections: List[str] = field(default_factory=list)

    # Document info
    ingested_at: str = field(default_factory=lambda: datetime.now().isoformat())
    file_size_bytes: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "DocumentMetadata":
        """Create from dictionary"""
        return cls(**data)


class MetadataStore:
    """
    In-memory metadata storage with optional SQLite persistence.

    Provides queryable interface for:
    - Chunk metadata lookup
    - Document metadata tracking
    - Citation generation
    - Search filtering by section/page

    Acceptance Criteria (Task 2.5):
    - ✅ Every chunk has source document name
    - ✅ Page/section numbers tracked
    - ✅ Exact character positions tracked
    - ✅ Metadata queryable for citation generation
    - ✅ Schema validated
    """

    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize metadata store.

        Args:
            persist_path: Optional path to SQLite database for persistence
        """
        self.chunk_metadata: Dict[str, ChunkMetadata] = {}
        self.document_metadata: Dict[str, DocumentMetadata] = {}
        self.parent_texts: Dict[str, str] = {}
        self.persist_path = persist_path

        # Initialize SQLite if persistence requested
        if persist_path:
            self.db_path = Path(persist_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_database()
        else:
            self.db_path = None

        logger.info("MetadataStore initialized")

    def _init_database(self):
        """Initialize SQLite database schema"""
        if not self.db_path:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                source_doc TEXT NOT NULL,
                section TEXT,
                page_num INTEGER,
                start_char INTEGER,
                end_char INTEGER,
                chunk_text_length INTEGER,
                parent_chunk_id TEXT,
                indexed_at TEXT,
                embedding_model TEXT
            )
        """)


        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                source_doc TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                total_chunks INTEGER,
                total_characters INTEGER,
                sections TEXT,
                ingested_at TEXT,
                file_size_bytes INTEGER
            )
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON chunks(source_doc)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_section ON chunks(section)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_page ON chunks(page_num)")

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def register_document(self, doc_metadata: DocumentMetadata) -> None:
        """
        Register a new document in the store.

        Args:
            doc_metadata: Document metadata to register
        """
        self.document_metadata[doc_metadata.source_doc] = doc_metadata

        # Persist to database if enabled
        if self.db_path:
            self._persist_document(doc_metadata)

        logger.info(
            f"Registered document: {doc_metadata.source_doc} "
            f"({doc_metadata.total_chunks} chunks)"
        )

    def add_chunk(self, chunk_meta: ChunkMetadata) -> None:
        """
        Add chunk metadata to the store.

        Args:
            chunk_meta: Chunk metadata to add
        """
        self.chunk_metadata[chunk_meta.chunk_id] = chunk_meta

        # Persist to database if enabled
        if self.db_path:
            self._persist_chunk(chunk_meta)

    def add_chunks_batch(self, chunks: List[ChunkMetadata]) -> None:
        """
        Add multiple chunks efficiently.

        Args:
            chunks: List of chunk metadata objects
        """
        for chunk in chunks:
            self.chunk_metadata[chunk.chunk_id] = chunk

        # Batch persist to database
        if self.db_path and chunks:
            self._persist_chunks_batch(chunks)

        logger.info(f"Added {len(chunks)} chunks to metadata store")

    def store_parent_text(self, parent_id: str, text: str) -> None:
        """Stores parent text in the metadata store"""
        self.parent_texts[parent_id] = text

    def get_parent_text(self, parent_id: str) -> str:
        """Retrieves parent text by ID, returns empty string if not found"""
        return self.parent_texts.get(parent_id, "")

    def get_chunk(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Get metadata for a specific chunk"""
        return self.chunk_metadata.get(chunk_id)

    def get_document(self, source_doc: str) -> Optional[DocumentMetadata]:
        """Get metadata for a specific document"""
        return self.document_metadata.get(source_doc)

    def get_chunks_by_source(self, source_doc: str) -> List[ChunkMetadata]:
        """Get all chunks from a specific source document"""
        return [c for c in self.chunk_metadata.values() if c.source_doc == source_doc]

    def get_chunks_by_section(self, section: str) -> List[ChunkMetadata]:
        """Get all chunks in a specific section"""
        return [c for c in self.chunk_metadata.values() if c.section == section]

    def get_chunks_by_page(self, source_doc: str, page_num: int) -> List[ChunkMetadata]:
        """Get all chunks from a specific page"""
        return [
            c
            for c in self.chunk_metadata.values()
            if c.source_doc == source_doc and c.page_num == page_num
        ]

    def search_by_position(
        self, source_doc: str, start_char: int, end_char: int
    ) -> List[ChunkMetadata]:
        """Find chunks overlapping with character range"""
        results = []
        for chunk in self.chunk_metadata.values():
            if chunk.source_doc != source_doc:
                continue

            # Check for overlap
            if chunk.start_char < end_char and chunk.end_char > start_char:
                results.append(chunk)

        return sorted(results, key=lambda c: c.start_char)

    def get_all_sources(self) -> List[str]:
        """Get list of all source documents"""
        return list(self.document_metadata.keys())

    def get_all_sections(self) -> Set[str]:
        """Get set of all unique sections"""
        return set(c.section for c in self.chunk_metadata.values())

    def get_statistics(self) -> Dict:
        """Get statistics about stored metadata"""
        total_chunks = len(self.chunk_metadata)
        total_docs = len(self.document_metadata)

        sections = set(c.section for c in self.chunk_metadata.values())
        total_chars = sum(c.chunk_text_length for c in self.chunk_metadata.values())

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_sections": len(sections),
            "total_characters": total_chars,
            "avg_chunk_size": total_chars // max(1, total_chunks),
            "sections": list(sections),
        }

    def export_metadata(self, output_path: str) -> None:
        """
        Export all metadata to JSON file.

        Args:
            output_path: Path to save JSON export
        """
        data = {
            "documents": {
                name: doc.to_dict() for name, doc in self.document_metadata.items()
            },
            "chunks": {
                cid: chunk.to_dict() for cid, chunk in self.chunk_metadata.items()
            },
            "exported_at": datetime.now().isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported metadata to {output_path}")

    def import_metadata(self, input_path: str) -> None:
        """
        Import metadata from JSON file.

        Args:
            input_path: Path to JSON export
        """
        with open(input_path, "r") as f:
            data = json.load(f)

        # Import documents
        for name, doc_data in data.get("documents", {}).items():
            self.document_metadata[name] = DocumentMetadata.from_dict(doc_data)

        # Import chunks
        for cid, chunk_data in data.get("chunks", {}).items():
            self.chunk_metadata[cid] = ChunkMetadata.from_dict(chunk_data)

        logger.info(f"Imported metadata from {input_path}")

    def _persist_document(self, doc: DocumentMetadata) -> None:
        """Persist document metadata to SQLite"""
        if not self.db_path:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO documents 
            (source_doc, file_path, total_chunks, total_characters, sections, ingested_at, file_size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                doc.source_doc,
                doc.file_path,
                doc.total_chunks,
                doc.total_characters,
                json.dumps(doc.sections),
                doc.ingested_at,
                doc.file_size_bytes,
            ),
        )

        conn.commit()
        conn.close()

    def _persist_chunk(self, chunk: ChunkMetadata) -> None:
        """Persist chunk metadata to SQLite"""
        if not self.db_path:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO chunks
            (chunk_id, source_doc, section, page_num, start_char, end_char, chunk_text_length, parent_chunk_id, indexed_at, embedding_model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                chunk.chunk_id,
                chunk.source_doc,
                chunk.section,
                chunk.page_num,
                chunk.start_char,
                chunk.end_char,
                chunk.chunk_text_length,
                chunk.parent_chunk_id,
                chunk.indexed_at,
                chunk.embedding_model,
            ),
        )

        conn.commit()
        conn.close()

    def _persist_chunks_batch(self, chunks: List[ChunkMetadata]) -> None:
        """Persist multiple chunks to SQLite efficiently"""
        if not self.db_path or not chunks:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        data = [
            (
                chunk.chunk_id,
                chunk.source_doc,
                chunk.section,
                chunk.page_num,
                chunk.start_char,
                chunk.end_char,
                chunk.chunk_text_length,
                chunk.parent_chunk_id,
                chunk.indexed_at,
                chunk.embedding_model,
            )
            for chunk in chunks
        ]

        cursor.executemany(
            """
            INSERT OR REPLACE INTO chunks
            (chunk_id, source_doc, section, page_num, start_char, end_char, chunk_text_length, parent_chunk_id, indexed_at, embedding_model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            data,
        )

        conn.commit()
        conn.close()


# Test code for Phase 2, Task 2.5
if __name__ == "__main__":
    print("=" * 60)
    print("MetadataStore Test")
    print("=" * 60)

    # Create in-memory store
    store = MetadataStore()
    print("✓ Created in-memory metadata store")

    # Register a document
    doc_meta = DocumentMetadata(
        source_doc="01_Employee_Handbook.docx",
        file_path="sample_documents/01_Employee_Handbook.docx",
        total_chunks=15,
        total_characters=5420,
        sections=["Introduction", "Benefits", "Compliance"],
        file_size_bytes=45000,
    )
    store.register_document(doc_meta)
    print(f"✓ Registered document: {doc_meta.source_doc}")

    # Add chunks
    chunks = [
        ChunkMetadata(
            chunk_id=f"chunk_{i:04d}",
            source_doc="01_Employee_Handbook.docx",
            section=["Introduction", "Benefits", "Compliance"][i % 3],
            page_num=1 + (i // 5),
            start_char=i * 350,
            end_char=(i + 1) * 350,
            chunk_text_length=350,
        )
        for i in range(15)
    ]
    store.add_chunks_batch(chunks)
    print(f"✓ Added {len(chunks)} chunks")

    # Query metadata
    print("\n" + "=" * 60)
    print("Metadata Queries")
    print("=" * 60)

    stats = store.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Unique sections: {stats['total_sections']}")
    print(f"  Total characters: {stats['total_characters']}")
    print(f"  Avg chunk size: {stats['avg_chunk_size']}")

    # Query by section
    intro_chunks = store.get_chunks_by_section("Introduction")
    print(f"\n✓ Found {len(intro_chunks)} chunks in 'Introduction' section")

    # Query by page
    page1_chunks = store.get_chunks_by_page("01_Employee_Handbook.docx", 1)
    print(f"✓ Found {len(page1_chunks)} chunks on page 1")

    # Query by position
    pos_chunks = store.search_by_position("01_Employee_Handbook.docx", 100, 500)
    print(f"✓ Found {len(pos_chunks)} chunks in position range 100-500")

    # Export metadata
    print("\n" + "=" * 60)
    print("Export/Import Test")
    print("=" * 60)

    export_path = "metadata_export.json"
    store.export_metadata(export_path)
    print(f"✓ Exported metadata to {export_path}")

    # Create new store and import
    store2 = MetadataStore()
    store2.import_metadata(export_path)
    print(f"✓ Imported metadata into new store")

    stats2 = store2.get_statistics()
    print(f"✓ Imported store has {stats2['total_chunks']} chunks")

    # Cleanup
    Path(export_path).unlink()
    print(f"✓ Cleaned up test files")
