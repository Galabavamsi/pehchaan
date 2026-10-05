import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// No StrictMode: the demo page POSTs a scenario on mount, and a double mount would reset the server twice.
createRoot(document.getElementById("root")!).render(<App />);
