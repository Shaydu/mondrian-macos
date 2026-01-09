# RAG Integration for iOS

Guide for implementing semantic image search using RAG (Retrieval-Augmented Generation) in your iOS app.

---

## What is RAG?

RAG enables **semantic search** of images using natural language queries. Instead of keyword matching, it understands the *meaning* of your query and finds visually similar images.

**Example:**
- Query: "sunset over mountains with dramatic lighting"
- Results: Images with similar composition, lighting, and subject matter

---

## How It Works

```
User Query → Embedding → Vector Search → Similar Images
              ↓
Image Upload → Caption → Embedding → Storage
```

### The Process:

1. **Caption Generation** - MLX vision model describes the image
2. **Embedding Creation** - Text converted to 384-dimensional vector
3. **Storage** - Vector stored in database with image metadata
4. **Search** - Query converted to vector, compared using cosine similarity

---

## Prerequisites

### Required Services

RAG requires three services (automatically started by monitoring service):

- **Caption Service** (5200) - Generates image descriptions
- **Embedding Service** (5300) - Creates vector embeddings  
- **RAG Service** (5400) - Orchestrates indexing and search

### Start Services

```bash
cd /Users/shaydu/dev/mondrian-macos
./mondrian.sh
```

### Verify RAG is Running

```bash
curl http://10.0.0.227:5400/health
```

Expected response:
```json
{
  "status": "UP",
  "database": "UP (15 captions indexed)",
  "caption_service": "http://127.0.0.1:5200",
  "embedding_service": "http://127.0.0.1:5300"
}
```

---

## iOS Implementation

### Step 1: Index an Image

After analysis completes, index the image for future searches.

```swift
struct IndexRequest: Encodable {
    let job_id: String
    let image_path: String
}

struct IndexResponse: Decodable {
    let success: Bool
    let id: String
    let caption: String
    let embedding_dim: Int
}

func indexImage(jobId: String, imagePath: String) async throws -> IndexResponse {
    let request = IndexRequest(
        job_id: jobId,
        image_path: imagePath  // e.g., "source/photo-abc123.jpg"
    )
    
    var urlRequest = URLRequest(url: URL(string: "http://10.0.0.227:5400/index")!)
    urlRequest.httpMethod = "POST"
    urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)
    
    let (data, response) = try await URLSession.shared.data(for: urlRequest)
    
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw RAGError.indexingFailed
    }
    
    return try JSONDecoder().decode(IndexResponse.self, from: data)
}
```

**When to Index:**
- Automatically after analysis completes
- In background to avoid blocking UI
- Only index images user wants to search later

**Example:**
```swift
// After receiving 'analysis_complete' event
eventSource.addEventListener("analysis_complete") { _, _, data in
    Task {
        // Index in background
        let imagePath = "source/\(uploadResponse.filename)"
        try? await indexImage(jobId: jobId, imagePath: imagePath)
    }
}
```

---

### Step 2: Search for Similar Images

Search indexed images using natural language.

```swift
struct SearchRequest: Encodable {
    let query: String
    let top_k: Int
}

struct SearchResult: Decodable {
    let id: String
    let job_id: String
    let image_path: String
    let caption: String
    let similarity: Double  // 0.0 to 1.0
}

struct SearchResponse: Decodable {
    let query: String
    let results: [SearchResult]
    let total: Int
}

func searchImages(query: String, topK: Int = 10) async throws -> SearchResponse {
    let request = SearchRequest(query: query, top_k: topK)
    
    var urlRequest = URLRequest(url: URL(string: "http://10.0.0.227:5400/search")!)
    urlRequest.httpMethod = "POST"
    urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)
    
    let (data, response) = try await URLSession.shared.data(for: urlRequest)
    
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw RAGError.searchFailed
    }
    
    return try JSONDecoder().decode(SearchResponse.self, from: data)
}
```

**Query Examples:**
- `"sunset over mountains"`
- `"architectural photography with strong lines"`
- `"portrait with dramatic lighting"`
- `"abstract close-up of flowers"`
- `"landscape in the style of Ansel Adams"`

---

## UI Components

### Search Bar

```swift
class SearchViewController: UIViewController, UISearchBarDelegate {
    let searchBar = UISearchBar()
    let api = MondrianAPIService()
    var searchResults: [SearchResult] = []
    
    override func viewDidLoad() {
        super.viewDidLoad()
        searchBar.delegate = self
        searchBar.placeholder = "Search images by description..."
    }
    
    func searchBarSearchButtonClicked(_ searchBar: UISearchBar) {
        guard let query = searchBar.text, !query.isEmpty else { return }
        performSearch(query: query)
    }
    
    func performSearch(query: String) {
        Task {
            do {
                let response = try await api.searchImages(query: query)
                self.searchResults = response.results
                DispatchQueue.main.async {
                    self.collectionView.reloadData()
                }
            } catch {
                showError("Search failed: \(error.localizedDescription)")
            }
        }
    }
}
```

### Results Grid

```swift
class SearchResultCell: UICollectionViewCell {
    let imageView = UIImageView()
    let similarityLabel = UILabel()
    let captionLabel = UILabel()
    
    func configure(with result: SearchResult, jobServiceURL: String) {
        // Load thumbnail
        let thumbnailURL = "\(jobServiceURL)/image/\(result.image_path)"
        loadImage(from: thumbnailURL)
        
        // Show similarity as percentage
        let percentage = Int(result.similarity * 100)
        similarityLabel.text = "\(percentage)% match"
        
        // Show caption preview
        captionLabel.text = String(result.caption.prefix(100))
    }
}

extension SearchViewController: UICollectionViewDataSource {
    func collectionView(_ collectionView: UICollectionView, 
                       numberOfItemsInSection section: Int) -> Int {
        return searchResults.count
    }
    
    func collectionView(_ collectionView: UICollectionView,
                       cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {
        let cell = collectionView.dequeueReusableCell(
            withReuseIdentifier: "ResultCell",
            for: indexPath
        ) as! SearchResultCell
        
        let result = searchResults[indexPath.row]
        cell.configure(with: result, jobServiceURL: api.jobServiceURL)
        return cell
    }
}
```

### Similarity Indicator

```swift
class SimilarityBadge: UIView {
    let progressView = UIProgressView(progressViewStyle: .bar)
    let label = UILabel()
    
    func setSimilarity(_ similarity: Double) {
        let percentage = Int(similarity * 100)
        progressView.progress = Float(similarity)
        label.text = "\(percentage)%"
        
        // Color coding
        if similarity > 0.8 {
            progressView.progressTintColor = .systemGreen
        } else if similarity > 0.6 {
            progressView.progressTintColor = .systemYellow
        } else {
            progressView.progressTintColor = .systemOrange
        }
    }
}
```

---

## Complete Example

```swift
class ImageAnalysisWithRAGViewController: UIViewController {
    let api = MondrianAPIService(host: "10.0.0.227")
    
    // MARK: - Full Workflow
    
    func analyzeAndIndexImage(_ imageData: Data) async {
        do {
            // Step 1: Upload and analyze
            let uploadResponse = try await api.uploadImage(imageData, advisor: "ansel")
            let jobId = uploadResponse.job_id
            let filename = uploadResponse.filename
            
            // Step 2: Monitor progress via SSE
            let eventSource = api.connectToStream(
                streamUrl: uploadResponse.stream_url,
                onProgress: { jobData in
                    self.updateProgress(jobData.progress_percentage)
                },
                onComplete: { html in
                    self.displayAnalysis(html: html)
                    
                    // Step 3: Index for RAG
                    Task {
                        await self.indexImageForSearch(
                            jobId: jobId,
                            filename: filename
                        )
                    }
                },
                onError: { error in
                    self.showError(error?.localizedDescription ?? "Unknown error")
                }
            )
            
        } catch {
            showError("Analysis failed: \(error.localizedDescription)")
        }
    }
    
    func indexImageForSearch(jobId: String, filename: String) async {
        do {
            let imagePath = "source/\(filename)"
            let response = try await api.indexImage(jobId: jobId, imagePath: imagePath)
            
            print("✅ Indexed: \(response.caption.prefix(100))")
            
            // Optionally show a success message
            DispatchQueue.main.async {
                self.showToast("Image indexed for search")
            }
            
        } catch {
            print("⚠️ Indexing failed: \(error.localizedDescription)")
            // Non-critical - don't show error to user
        }
    }
    
    func searchSimilarImages(query: String) async {
        do {
            let response = try await api.searchImages(query: query, topK: 20)
            
            DispatchQueue.main.async {
                self.displaySearchResults(response.results)
            }
            
        } catch {
            showError("Search failed: \(error.localizedDescription)")
        }
    }
    
    // MARK: - UI Updates
    
    func updateProgress(_ percentage: Int) {
        progressBar.progress = Float(percentage) / 100.0
        statusLabel.text = "Analyzing... \(percentage)%"
    }
    
    func displayAnalysis(html: String) {
        webView.loadHTMLString(html, baseURL: URL(string: api.jobServiceURL))
    }
    
    func displaySearchResults(_ results: [SearchResult]) {
        searchResultsView.results = results
        searchResultsView.reloadData()
    }
    
    func showToast(_ message: String) {
        // Show temporary notification
        let toast = UILabel()
        toast.text = message
        toast.backgroundColor = .systemGreen
        toast.textColor = .white
        toast.textAlignment = .center
        toast.frame = CGRect(x: 20, y: view.bounds.height - 100, 
                            width: view.bounds.width - 40, height: 50)
        view.addSubview(toast)
        
        UIView.animate(withDuration: 2.0, delay: 1.0, options: .curveEaseOut) {
            toast.alpha = 0
        } completion: { _ in
            toast.removeFromSuperview()
        }
    }
}
```

---

## Testing RAG

### Manual Testing

```bash
# 1. Index a test image
curl -X POST http://10.0.0.227:5400/index \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-001",
    "image_path": "source/test-image.jpg"
  }'

# 2. Search for similar images
curl -X POST http://10.0.0.227:5400/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "landscape photography",
    "top_k": 5
  }'
```

### iOS Unit Tests

```swift
class RAGIntegrationTests: XCTestCase {
    let api = MondrianAPIService(host: "10.0.0.227")
    
    func testIndexImage() async throws {
        let response = try await api.indexImage(
            jobId: "test-job-123",
            imagePath: "source/test-photo.jpg"
        )
        
        XCTAssertTrue(response.success)
        XCTAssertFalse(response.caption.isEmpty)
        XCTAssertEqual(response.embedding_dim, 384)
    }
    
    func testSearchImages() async throws {
        let response = try await api.searchImages(query: "sunset")
        
        XCTAssertFalse(response.results.isEmpty)
        XCTAssertEqual(response.query, "sunset")
        
        // Results should be sorted by similarity (highest first)
        for i in 0..<response.results.count - 1 {
            XCTAssertGreaterThanOrEqual(
                response.results[i].similarity,
                response.results[i + 1].similarity
            )
        }
    }
    
    func testRAGAvailability() async throws {
        let url = URL(string: "http://10.0.0.227:5400/health")!
        let (data, response) = try await URLSession.shared.data(from: url)
        
        let httpResponse = response as! HTTPURLResponse
        XCTAssertEqual(httpResponse.statusCode, 200)
        
        let health = try JSONDecoder().decode(RAGHealth.self, from: data)
        XCTAssertEqual(health.status, "UP")
    }
}
```

---

## Error Handling

```swift
enum RAGError: Error, LocalizedError {
    case serviceUnavailable
    case indexingFailed
    case searchFailed
    case invalidImagePath
    case networkError(Error)
    
    var errorDescription: String? {
        switch self {
        case .serviceUnavailable:
            return "RAG service is not available. Please check if all services are running."
        case .indexingFailed:
            return "Failed to index image for search."
        case .searchFailed:
            return "Search operation failed."
        case .invalidImagePath:
            return "Invalid image path provided."
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

extension MondrianAPIService {
    func checkRAGAvailability() async -> Bool {
        guard let url = URL(string: "\(ragServiceURL)/health") else {
            return false
        }
        
        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
    
    func indexImageSafely(jobId: String, imagePath: String) async -> Bool {
        guard await checkRAGAvailability() else {
            print("RAG service unavailable - skipping indexing")
            return false
        }
        
        do {
            _ = try await indexImage(jobId: jobId, imagePath: imagePath)
            return true
        } catch {
            print("Indexing failed: \(error.localizedDescription)")
            return false
        }
    }
}
```

---

## Performance Tips

### 1. Index in Background

Don't block the main thread or user flow:

```swift
Task.detached(priority: .background) {
    try? await api.indexImage(jobId: jobId, imagePath: imagePath)
}
```

### 2. Cache Search Results

```swift
class SearchCache {
    private var cache: [String: SearchResponse] = [:]
    private let expirationTime: TimeInterval = 300 // 5 minutes
    
    func get(query: String) -> SearchResponse? {
        return cache[query]
    }
    
    func set(query: String, response: SearchResponse) {
        cache[query] = response
    }
}
```

### 3. Batch Operations

If indexing multiple images:

```swift
func indexMultipleImages(_ images: [(jobId: String, imagePath: String)]) async {
    await withTaskGroup(of: Void.self) { group in
        for image in images {
            group.addTask {
                try? await self.api.indexImage(
                    jobId: image.jobId,
                    imagePath: image.imagePath
                )
            }
        }
    }
}
```

### 4. Prefetch Similar Images

After indexing, prefetch a few similar images to show recommendations:

```swift
func prefetchRecommendations(caption: String) async {
    let query = String(caption.prefix(100))
    let results = try? await api.searchImages(query: query, topK: 5)
    // Cache or display recommendations
}
```

---

## Troubleshooting

### RAG Service Not Available

**Symptom:** Index or search requests fail with connection error

**Solution:**
```bash
# Check service status
curl http://10.0.0.227:5400/health

# Restart services
cd /Users/shaydu/dev/mondrian-macos
./mondrian.sh --restart
```

### No Search Results

**Symptom:** Search returns empty results array

**Possible causes:**
- No images have been indexed yet
- Query is too specific
- Database is empty

**Solution:**
- Index some test images first
- Try broader queries
- Check database has captions: `curl http://10.0.0.227:5400/health`

### Low Similarity Scores

**Symptom:** All results have similarity < 0.5

**This is normal** when:
- Query doesn't match indexed content
- Limited images in database
- Query is very specific

**Interpretation:**
- `> 0.8` - Very similar
- `0.6 - 0.8` - Moderately similar
- `0.4 - 0.6` - Somewhat similar
- `< 0.4` - Not very similar

---

## Architecture

```
┌─────────────────────────────────────────┐
│          iOS Application                │
└─────────────────┬───────────────────────┘
                  │
                  │ HTTP/JSON
                  │
┌─────────────────▼───────────────────────┐
│        RAG Service (Port 5400)          │
│  - Index endpoint                       │
│  - Search endpoint                      │
└─────┬─────────────────────┬─────────────┘
      │                     │
      │ HTTP                │ HTTP
      │                     │
┌─────▼──────────┐  ┌───────▼──────────┐
│Caption Service │  │Embedding Service │
│  (Port 5200)   │  │  (Port 5300)     │
│  - MLX Vision  │  │  - sentence-bert │
│  - Qwen3-VL    │  │  - 384-dim       │
└────────────────┘  └──────────────────┘
                          │
                          │
                  ┌───────▼───────┐
                  │  mondrian.db  │
                  │image_captions │
                  └───────────────┘
```

---

## Next Steps

1. **Implement Basic Search** - Add search bar and results view
2. **Auto-Index** - Index images after analysis completes
3. **Polish UI** - Show similarity scores, captions, thumbnails
4. **Add Filters** - Filter by advisor, date, or score range
5. **Recommendations** - Show "similar images" after analysis

---

## Additional Resources

- **Main API Guide**: `/docs/ios/API_INTEGRATION.md`
- **RAG Quick Start**: `/docs/RAG_QUICKSTART.md`
- **Test Script**: `/test/test_ios_api_flow.sh`

---

**Questions?** The RAG system is production-ready and tested. Contact the Mondrian team for support.
