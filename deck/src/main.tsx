import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// No StrictMode: its dev double-mount tears down the R3F root and drei <Html> roots mid-render.
createRoot(document.getElementById("root")!).render(<App />);
