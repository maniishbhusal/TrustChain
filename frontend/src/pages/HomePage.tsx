import { useEffect, useState } from "react";
import UploadPanel from "../components/Home/UploadPanel";
import Leaderboard from "@/components/Leaderboard";
import AskQuestions from "@/components/AskQuestions";
import { useLogin } from "@/context/UserContext";
import { SuiObjectData } from "@mysten/sui.js/client";
import LoggedOutView from "@/components/Home/LoggedOutView";
import { Loader } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";

const HomePage = () => {
  const { isLoggedIn, userDetails } = useLogin();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  // const [userContentIds, setUserContentIds] = useState<string[]>([]);
  // const [userContentObjects, setUserContentObjects] = useState<SuiObjectData[]>(
  //   []
  // );
  const [isRegistered, setIsRegistered] = useState<boolean>(false);
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);

  const handleRegisterNowClick = (e: any) => {
    e.preventDefault();
    e.stopPropagation();
    setIsProfileDialogOpen(true);
  };

  useEffect(() => {
    if (isLoggedIn && userDetails?.address) {
    }
  }, [isLoggedIn, userDetails]);

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {isLoading && (
        <div className="flex justify-center items-center py-4">
          <Loader className="animate-spin" />
        </div>
      )}

      {error && (
        <div className="mb-4">
          <span className="text-red-500">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-6">
          {isLoggedIn ? (
            <>
              {isRegistered ? (
                <UploadPanel />
              ) : (
                <div className="border rounded-md p-4 flex flex-col gap-6 items-center">
                  <span>
                    Register as a Content Creator to upload your content on
                    TrustChain.
                  </span>
                  <Button onClick={handleRegisterNowClick}>Register now</Button>
                  <Dialog
                    open={isProfileDialogOpen}
                    onOpenChange={setIsProfileDialogOpen}
                  >
                    {/* <DialogContent className="sm:max-w-md">
                      <CreateProfile />
                    </DialogContent> */}
                  </Dialog>
                </div>
              )}
            </>
          ) : (
            <LoggedOutView />
          )}
        </div>

        {isLoggedIn && (
          <div className="lg:col-span-4 space-y-6">
            <div className="sticky">
              {/* <Leaderboard /> */}
              <div className="">
                {/* <AskQuestions /> */}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HomePage;
