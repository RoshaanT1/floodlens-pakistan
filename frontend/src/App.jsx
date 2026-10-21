import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter, HashRouter, Route, Routes } from 'react-router-dom';

// The Hugging Face Space is a static host: hash routes, and the pipeline's Live data page first.
const STATIC_SPACE = import.meta.env.VITE_STATIC_SPACE === '1';
const Router = STATIC_SPACE ? HashRouter : BrowserRouter;
import PageNotFound from './lib/PageNotFound';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import UserNotRegisteredError from '@/components/UserNotRegisteredError';
import ScrollToTop from './components/ScrollToTop';
import { ThemeProvider } from '@/lib/theme';
import SituationRoom from '@/pages/SituationRoom';
import FoodPrices from '@/pages/FoodPrices';
import SourcesMethods from '@/pages/SourcesMethods';
import LiveData from '@/pages/LiveData';
import Ask from '@/pages/Ask';
// Add page imports here

const AuthenticatedApp = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError, navigateToLogin } = useAuth();

  // Show loading spinner while checking app public settings or auth
  if (isLoadingPublicSettings || isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
      </div>
    );
  }

  // Handle authentication errors
  if (authError) {
    if (authError.type === 'user_not_registered') {
      return <UserNotRegisteredError />;
    } else if (authError.type === 'auth_required') {
      // Redirect to login automatically
      navigateToLogin();
      return null;
    }
  }

  // Render the main app
  return (
    <Routes>
      {/* Add your page Route elements here */}
      <Route path="/" element={STATIC_SPACE ? <LiveData /> : <SituationRoom />} />
      <Route path="/situation" element={<SituationRoom />} />
      <Route path="/food-prices" element={<FoodPrices />} />
      <Route path="/sources" element={<SourcesMethods />} />
      <Route path="/live" element={<LiveData />} />
      <Route path="/ask" element={<Ask />} />
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
};


function App() {

  return (
    <ThemeProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClientInstance}>
          <Router>
            <ScrollToTop />
            <AuthenticatedApp />
          </Router>
          <Toaster />
        </QueryClientProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App