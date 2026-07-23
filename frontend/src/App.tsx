import { SyncDualPlayer } from './components/SyncDualPlayer';
import './index.css';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:bg-none dark:bg-[#191919] text-gray-900 dark:text-gray-100 transition-colors duration-300">
      <SyncDualPlayer />
    </div>
  );
}

export default App;
