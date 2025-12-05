const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, PageNumber, LevelFormat } = require('docx');
const fs = require('fs');

// Colors
const headerFill = "1E3A5F";
const lightBlueFill = "E8F4FD";
const lightGreenFill = "E8F8E8";
const lightYellowFill = "FFF9E6";

const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 48, bold: true, color: "1E3A5F", font: "Arial" },
        paragraph: { spacing: { after: 200 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: "1E3A5F", font: "Arial" },
        paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: "2563EB", font: "Arial" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "374151", font: "Arial" },
        paragraph: { spacing: { before: 150, after: 80 }, outlineLevel: 2 } },
      { id: "Code", name: "Code", basedOn: "Normal",
        run: { font: "Courier New", size: 20 },
        paragraph: { spacing: { before: 100, after: 100 } } }
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-prereq",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-steps",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-storage",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-verify",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "Elder Trading System - Deployment Guide", italics: true, color: "6B7280", size: 18 })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 18 }), new TextRun({ children: [PageNumber.CURRENT], size: 18 }), 
                   new TextRun({ text: " of ", size: 18 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18 })]
      })] })
    },
    children: [
      // Title
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Elder Trading System")] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
        children: [new TextRun({ text: "Azure Deployment Guide & Application Documentation", size: 24, color: "6B7280" })] }),

      // Executive Summary
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Executive Summary")] }),
      new Paragraph({ spacing: { after: 150 },
        children: [new TextRun("This document provides complete deployment instructions for the Elder Trading System, a web application implementing Dr. Alexander Elder's Triple Screen Trading methodology for NASDAQ/S&P 500 and NSE markets.")] }),

      // Key Features Table
      new Table({
        columnWidths: [3120, 6240],
        rows: [
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR }, columnSpan: 2,
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "KEY FEATURES", bold: true, color: "FFFFFF" })] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 3120, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Daily Checklist", bold: true })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 6240, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun("7-step evening analysis workflow with progress tracking")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 3120, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Weekly Screener", bold: true })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 6240, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun("Screen 1 analysis - EMA slope + MACD-Histogram for trend")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 3120, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Daily Screener", bold: true })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 6240, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun("Screen 2 analysis - Force Index, Stochastic, price vs EMA")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 3120, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Trade APGAR", bold: true })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 6240, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun("Configurable scoring system with position sizing calculator")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 3120, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Trade Journal", bold: true })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 6240, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun("Complete trade logging with P&L tracking and statistics")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 3120, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun({ text: "Risk Management", bold: true })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 6240, type: WidthType.DXA },
                children: [new Paragraph({ children: [new TextRun("2% per trade, 6% monthly drawdown, configurable R:R targets")] })] })
            ]
          })
        ]
      }),

      // Architecture
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Architecture Overview")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 Technology Stack")] }),
      
      new Table({
        columnWidths: [3120, 6240],
        rows: [
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Component", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Technology", bold: true, color: "FFFFFF" })] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Backend")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Python 3.11 + Flask + Gunicorn")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Frontend")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("React 18 + Tailwind CSS (Single HTML file)")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Database")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("SQLite (persistent via Azure Files)")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Market Data")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Yahoo Finance (yfinance library)")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Hosting")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Azure App Service (F1 Free Tier)")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Storage")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Azure Files (included with App Service)")] })] })
            ]
          })
        ]
      }),

      // Prerequisites
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Prerequisites")] }),
      
      new Paragraph({ numbering: { reference: "numbered-prereq", level: 0 },
        children: [new TextRun({ text: "Azure Account: ", bold: true }), new TextRun("Free tier is sufficient. Sign up at portal.azure.com")] }),
      new Paragraph({ numbering: { reference: "numbered-prereq", level: 0 },
        children: [new TextRun({ text: "Azure CLI: ", bold: true }), new TextRun("Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")] }),
      new Paragraph({ numbering: { reference: "numbered-prereq", level: 0 },
        children: [new TextRun({ text: "Git: ", bold: true }), new TextRun("For source control and deployment")] }),
      new Paragraph({ numbering: { reference: "numbered-prereq", level: 0 },
        children: [new TextRun({ text: "Python 3.11: ", bold: true }), new TextRun("For local testing (optional)")] }),

      // Deployment Steps
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Azure Deployment Steps")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 Login to Azure")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az login")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 Create Resource Group")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az group create --name elder-trading-rg --location uksouth")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.3 Create App Service Plan (Free Tier)")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az appservice plan create --name elder-trading-plan --resource-group elder-trading-rg --sku F1 --is-linux")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.4 Create Web App")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp create --name elder-trading-app --resource-group elder-trading-rg --plan elder-trading-plan --runtime \"PYTHON:3.11\"")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.5 Configure Startup Command")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp config set --name elder-trading-app --resource-group elder-trading-rg --startup-file \"gunicorn --bind=0.0.0.0:8000 app:app\"")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.6 Deploy the Application")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun("Option A: Deploy from local folder:")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp up --name elder-trading-app --resource-group elder-trading-rg")] }),
      
      new Paragraph({ spacing: { before: 150, after: 100 },
        children: [new TextRun("Option B: Deploy from GitHub (recommended for CI/CD):")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp deployment source config --name elder-trading-app --resource-group elder-trading-rg --repo-url https://github.com/yourusername/elder-trading-system --branch main")] }),

      // Persistent Storage
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Persistent Storage Setup")] }),
      
      new Paragraph({ spacing: { after: 150 }, shading: { fill: lightYellowFill, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "Important: ", bold: true }), new TextRun("Azure App Service's local filesystem is ephemeral. To persist data between deployments and restarts, use Azure Files.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 Create Storage Account")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az storage account create --name eldertradingstorage --resource-group elder-trading-rg --location uksouth --sku Standard_LRS")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 Create File Share")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az storage share create --name elder-data --account-name eldertradingstorage")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.3 Get Storage Key")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az storage account keys list --account-name eldertradingstorage --query [0].value -o tsv")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.4 Mount to Web App")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp config storage-account add --name elder-trading-app --resource-group elder-trading-rg --custom-id ElderData --storage-type AzureFiles --share-name elder-data --account-name eldertradingstorage --access-key <YOUR_KEY> --mount-path /home/data")] }),

      // Environment Variables
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Environment Configuration")] }),
      
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp config appsettings set --name elder-trading-app --resource-group elder-trading-rg --settings DATABASE_PATH=/home/data/elder_trading.db SECRET_KEY=your-secret-key-here")] }),

      // Verification
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. Verification")] }),
      
      new Paragraph({ numbering: { reference: "numbered-verify", level: 0 },
        children: [new TextRun("Open browser and navigate to: https://elder-trading-app.azurewebsites.net")] }),
      new Paragraph({ numbering: { reference: "numbered-verify", level: 0 },
        children: [new TextRun("Verify the Daily Checklist loads correctly")] }),
      new Paragraph({ numbering: { reference: "numbered-verify", level: 0 },
        children: [new TextRun("Run the Weekly Screener and verify data loads from Yahoo Finance")] }),
      new Paragraph({ numbering: { reference: "numbered-verify", level: 0 },
        children: [new TextRun("Check the Trade Journal persists data after page refresh")] }),

      // API Endpoints
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("8. API Reference")] }),

      new Table({
        columnWidths: [2340, 3120, 3900],
        rows: [
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Method", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Endpoint", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Description", bold: true, color: "FFFFFF" })] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("GET")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/health")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Health check")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightBlueFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("POST")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/screener/weekly")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Run weekly screener")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightBlueFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("POST")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/screener/daily")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Run daily screener")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("GET")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/stock/<symbol>")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Get stock analysis")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("GET")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/strategies")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Get APGAR strategies")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("GET")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/journal")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Get trade journal")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightBlueFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("POST")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/journal")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Create journal entry")] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun("GET")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("/api/settings")] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Get account settings")] })] })
            ]
          })
        ]
      }),

      // Troubleshooting
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("9. Troubleshooting")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("9.1 View Application Logs")] }),
      new Paragraph({ style: "Code", shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
        children: [new TextRun("az webapp log tail --name elder-trading-app --resource-group elder-trading-rg")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("9.2 Common Issues")] }),
      
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "502 Bad Gateway: ", bold: true }), new TextRun("Check startup command and requirements.txt")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Database not persisting: ", bold: true }), new TextRun("Verify Azure Files mount is configured")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Yahoo Finance errors: ", bold: true }), new TextRun("Check rate limiting, add delays between requests")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Slow response: ", bold: true }), new TextRun("Free tier has cold start. Consider B1 tier for production")] }),

      // Cost Estimation
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("10. Cost Estimation")] }),

      new Table({
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Resource", bold: true, color: "FFFFFF" })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: headerFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "Monthly Cost", bold: true, color: "FFFFFF" })] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("App Service (F1 Free)")] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "£0.00", bold: true })] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun("Azure Files (5GB)")] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "~£0.10", bold: true })] })] })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: lightYellowFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "TOTAL", bold: true })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: lightGreenFill, type: ShadingType.CLEAR },
                children: [new Paragraph({ children: [new TextRun({ text: "~£0.10/month", bold: true })] })] })
            ]
          })
        ]
      }),

      // Footer
      new Paragraph({ spacing: { before: 400 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Elder Trading System v1.0 | Based on Dr. Alexander Elder's Triple Screen Methodology", italics: true, color: "6B7280", size: 18 })] })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/mnt/user-data/outputs/Elder_Trading_Azure_Deployment_Guide.docx', buffer);
  console.log('Deployment guide created successfully!');
});
