/**
 * Export utilities for tabular data (CSV) and printable executive reports (PDF).
 */

export function exportToCsv(filename: string, rows: Record<string, any>[]): void {
  if (!rows || rows.length === 0) {
    alert("No records available to export.");
    return;
  }

  const headers = Object.keys(rows[0]);
  const csvRows: string[] = [];

  // Header row
  csvRows.push(headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(","));

  // Data rows
  for (const row of rows) {
    const values = headers.map((header) => {
      const val = row[header];
      if (val === null || val === undefined) {
        return '""';
      }
      if (typeof val === "object") {
        return `"${JSON.stringify(val).replace(/"/g, '""')}"`;
      }
      return `"${String(val).replace(/"/g, '""')}"`;
    });
    csvRows.push(values.join(","));
  }

  const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(csvRows.join("\n"));
  const link = document.createElement("a");
  link.setAttribute("href", csvContent);
  link.setAttribute("download", `${filename}_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function exportToPdf(_printableElementId?: string, documentTitle?: string): void {
  const originalTitle = document.title;
  if (documentTitle) {
    document.title = documentTitle;
  }

  // Trigger standard browser print which saves to vector PDF
  window.print();

  if (documentTitle) {
    document.title = originalTitle;
  }
}
