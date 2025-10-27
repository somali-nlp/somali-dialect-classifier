# Quick Reference - Backend Data Aggregation

## File Locations

### Scripts
```
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/scripts/generate_advanced_viz_data.py
```

### Documentation
```
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/DATA_AGGREGATION_BACKEND.md
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/BACKEND_ADDITIONS_SUMMARY.md
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/BACKEND_IMPLEMENTATION_COMPLETE.md
```

### Generated Data Files
```
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/_site/data/sankey_flow.json
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/_site/data/text_distributions.json
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/_site/data/comparison_metadata.json
```

### Modified Files
```
/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier/dashboard/build-site.sh
```

## Quick Commands

### Generate Data
```bash
cd /Users/ilyas/Desktop/Computer\ Programming/somali-nlp-projects/somali-dialect-classifier
python scripts/generate_advanced_viz_data.py
```

### Build Site
```bash
cd /Users/ilyas/Desktop/Computer\ Programming/somali-nlp-projects/somali-dialect-classifier
bash dashboard/build-site.sh
```

### Validate Data
```bash
python -m json.tool _site/data/sankey_flow.json
python -m json.tool _site/data/text_distributions.json
python -m json.tool _site/data/comparison_metadata.json
```

## API Endpoints (Static)

When dashboard is deployed:
- `GET /data/sankey_flow.json` - Pipeline flow data
- `GET /data/text_distributions.json` - Distribution data
- `GET /data/comparison_metadata.json` - Comparison data

## Frontend Integration Example

```javascript
// Fetch Sankey data
fetch('/data/sankey_flow.json')
  .then(r => r.json())
  .then(data => {
    // data.nodes, data.links, data.filter_breakdown
  });

// Fetch distributions
fetch('/data/text_distributions.json')
  .then(r => r.json())
  .then(data => {
    // data.sources, data.distributions
  });

// Fetch comparisons
fetch('/data/comparison_metadata.json')
  .then(r => r.json())
  .then(data => {
    // data.comparisons
  });
```

## Status

✅ **Implementation Complete**
✅ **All Tests Passing**
✅ **Production Ready**

Last Updated: October 27, 2025
