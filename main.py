from api.limitless_api import get_lifelogs
from api.bee_api import get_conversations, get_conversation_details
from api.data_sync import DataSyncer
from config import LIMITLESS_API_KEY, BEE_API_KEY, JSON_TEST
from direct_markdown_generation import generate_markdown_files, clear_vector_store_and_add_sample_data

def main():
    """
    Main function to fetch data from both Limitless and Bee APIs and generate markdown
    """
    print("=== Starting Data Sync and Markdown Generation ===")
    
    # Initialize data syncer
    syncer = DataSyncer()
    
    # Fetch data from both APIs
    print("\n=== Fetching Data ===")
    data = syncer.synchronize_data(days=90, limit_per_day=None)  # Fetch last 90 days of data
    
    if not data:
        print("No data retrieved from APIs")
        return
        
    # Prepare documents for vector storage
    print("\n=== Processing Data ===")
    documents = DataSyncer.combine_data_for_vector_storage(data)
    print(f"Processed {len(documents)} documents")
    
    # Group documents by source and date for markdown generation
    docs_by_source_date = {}
    for doc in documents:
        source = doc.get('source', '').lower()
        date = doc.get('date')
        if not source or not date:
            continue
            
        if source not in docs_by_source_date:
            docs_by_source_date[source] = {}
        if date not in docs_by_source_date[source]:
            docs_by_source_date[source][date] = []
            
        docs_by_source_date[source][date].append(doc)
    
    # Generate markdown files
    print("\n=== Generating Markdown ===")
    results = generate_markdown_files(docs_by_source_date)
    
    # Print summary
    print("\n=== Summary ===")
    limitless_count = sum(len(docs) for docs in docs_by_source_date.get('limitless', {}).values())
    bee_count = sum(len(docs) for docs in docs_by_source_date.get('bee', {}).values())
    print(f"Processed {limitless_count} Limitless documents")
    print(f"Processed {bee_count} Bee documents")
    print(f"Generated {len(results)} markdown files")

if __name__ == "__main__":
    main()