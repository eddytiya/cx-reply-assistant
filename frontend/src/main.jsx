import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import AuthRoot from "./components/AuthRoot";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthRoot />
  </StrictMode>
);
