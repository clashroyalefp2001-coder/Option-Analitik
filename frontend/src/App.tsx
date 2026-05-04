/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Data } from "./pages/Data";
import { TradesSearch } from "./pages/TradesSearch";
import { Training } from "./pages/Training";
import { Logs } from "./pages/Logs";

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/data" element={<Data />} />
          <Route path="/trades" element={<TradesSearch />} />
          <Route path="/training" element={<Training />} />
          <Route path="/logs" element={<Logs />} />
        </Routes>
      </Layout>
    </Router>
  );
}

