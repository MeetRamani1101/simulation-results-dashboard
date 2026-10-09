import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ComponentDetailPage from "./pages/ComponentDetailPage";
import DashboardPage from "./pages/DashboardPage";
import DemandsPage from "./pages/DemandsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/components/:componentId" element={<ComponentDetailPage />} />
        <Route path="/demands" element={<DemandsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
