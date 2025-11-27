#!/bin/bash

# Compile the LaTeX project report to PDF
# This script requires pdflatex to be installed

echo "Compiling F1 Streaming Pipeline Project Report..."
echo "=================================================="

# Check if pdflatex is available
if ! command -v pdflatex &> /dev/null; then
    echo "ERROR: pdflatex not found!"
    echo ""
    echo "Install LaTeX on macOS:"
    echo "  brew install --cask mactex"
    echo ""
    echo "Or use a smaller distribution:"
    echo "  brew install --cask basictex"
    echo "  sudo tlmgr update --self"
    echo "  sudo tlmgr install geometry hyperref listings xcolor amsmath booktabs caption subcaption float"
    exit 1
fi

# Compile the report (run twice for references)
echo ""
echo "Running pdflatex (first pass)..."
pdflatex -interaction=nonstopmode project_report.tex > /dev/null 2>&1

echo "Running pdflatex (second pass for references)..."
pdflatex -interaction=nonstopmode project_report.tex > /dev/null 2>&1

# Check if PDF was created
if [ -f "project_report.pdf" ]; then
    echo ""
    echo "✅ SUCCESS! PDF created: project_report.pdf"
    echo ""
    
    # Get file size
    size=$(ls -lh project_report.pdf | awk '{print $5}')
    pages=$(pdfinfo project_report.pdf 2>/dev/null | grep Pages | awk '{print $2}')
    
    echo "File size: $size"
    if [ ! -z "$pages" ]; then
        echo "Page count: $pages pages"
    fi
    
    echo ""
    echo "Opening PDF..."
    open project_report.pdf
    
    # Clean up auxiliary files
    echo ""
    read -p "Remove auxiliary files (.aux, .log, .toc)? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f project_report.aux project_report.log project_report.toc project_report.out
        echo "✅ Cleaned up auxiliary files"
    fi
else
    echo ""
    echo "❌ ERROR: PDF compilation failed!"
    echo ""
    echo "Check project_report.log for details:"
    tail -20 project_report.log
    exit 1
fi

