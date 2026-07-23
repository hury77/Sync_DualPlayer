const { jsPDF } = require("jspdf");
const fs = require("fs");
const base64Content = fs.readFileSync("./src/utils/Roboto-Regular.ts", "utf-8");
const match = base64Content.match(/`([^`]*)`/);
const robotoBase64 = match ? match[1] : "";

try {
  const doc = new jsPDF();
  doc.addFileToVFS("Roboto-Regular.ttf", robotoBase64);
  doc.addFont("Roboto-Regular.ttf", "Roboto", "normal");
  doc.setFont("Roboto", "normal");
  doc.text("Hello ąćęł", 10, 10);
  console.log("Success");
} catch(e) {
  console.error("Error:", e);
}
