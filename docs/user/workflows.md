# Workflows

## Importing Documents

### Supported Formats

- PDF lab reports
- PNG/JPG/JPEG images of lab results
- Maximum file size: 50 MB (configurable)

### Steps

1. Navigate to **Documents** in the sidebar
2. Click **Import Document**
3. Select your lab report file (PDF or image)
4. Wait for processing (extraction happens automatically)
5. Review the extracted observations

### What Happens During Import

1. The document is uploaded and stored securely
2. Text is extracted from the PDF (or OCR for images, if enabled)
3. Lab values are automatically identified and parsed
4. Observations are created with source provenance links

## Reviewing Observations

### Viewing Your Results

1. Navigate to **Observations** in the sidebar
2. Browse all extracted lab values
3. Use filters to narrow by analyte, date range, or abnormal status
4. Click any observation for full details including source document

### Verifying Accuracy

After import, you should verify extracted values:

1. Click an observation to view details
2. Compare with your original document
3. Click **Verify** to confirm accuracy, or edit if needed
4. Verified observations are marked with a checkmark

### Viewing Trends

1. Navigate to **Trends** or click an analyte name
2. View historical values plotted over time
3. Reference ranges are shown as shaded bands
4. Hover over data points for exact values and dates

### Lab Panels

View related tests together:

1. Navigate to **Panels**
2. Select a panel type: CBC, CMP, Lipid, or Thyroid
3. See all related observations in context

## AI Interpretations

### Getting an Interpretation

1. View an observation's details
2. Click **Interpret** to generate an AI explanation
3. The interpretation includes:
   - What the value means
   - Whether it's within normal range
   - Potential clinical significance
   - Related biomarkers to watch

### Panel Interpretations

1. Navigate to a lab panel (CBC, CMP, etc.)
2. Click **Interpret Panel** for a holistic analysis
3. Get an integrated view of how values relate to each other

### AI Assistant Chat

1. Navigate to **Assistant** in the sidebar
2. Ask questions about your results in natural language
3. The assistant uses your actual lab data for grounded answers
4. Example questions:
   - "What does my hemoglobin level mean?"
   - "How has my cholesterol changed over the past year?"
   - "What should I ask my doctor about my thyroid results?"

## Medication Management

### Adding a Medication

1. Navigate to **Medications** in the sidebar
2. Click **Add Medication**
3. Enter medication name, dosage, and frequency
4. Optionally add notes (e.g., "take with food")

### Setting Up Schedules

1. Open a medication's detail page
2. Click **Add Schedule**
3. Set the time and frequency
4. Enable notifications if desired

### Logging Doses

1. On the medication page, click **Log Dose**
2. Mark as **Taken** or **Skipped**
3. Optionally add a timestamp and notes
4. View adherence statistics on the medication detail page

### Adherence Tracking

- View adherence percentages per medication
- See dose history and patterns
- Use pattern learning to identify trends

## Exporting Data

### Doctor Summary

1. Navigate to **Export**
2. Click **Generate Doctor Summary**
3. A clinician-ready report is created with:
   - Recent lab results and trends
   - Abnormal values highlighted
   - Medication list and adherence
4. Download as a formatted document

### Discussion Questions

1. In the Export section, click **Generate Questions**
2. Get suggested questions to ask your doctor based on your data

### Data Export

1. Navigate to **Export**
2. Choose format: **CSV** or **JSON**
3. Download your complete observation history
4. Use for personal records or sharing with healthcare providers

## Model Settings

### Hardware Detection

1. Navigate to **Settings > Model**
2. Click **Detect Hardware** to assess your system
3. The app recommends a model tier based on your hardware

### Choosing a Model Tier

- **Low**: Fast, lightweight models (works on any hardware)
- **Mid**: Balanced performance and quality
- **High**: Best quality (requires powerful GPU)

### External API (Optional)

For users who prefer cloud AI:

1. Navigate to **Settings > Model > External API**
2. Choose provider (OpenAI or Anthropic)
3. Enter your API key (stored locally, never transmitted)
4. Select a model
