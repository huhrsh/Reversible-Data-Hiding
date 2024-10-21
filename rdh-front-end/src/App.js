import { useState } from "react";
import embed from "./assets/Secure data-cuate.png";
import extract from "./assets/Hacker-cuate.png";
import Embed from "./components/Embed";
import { ToastContainer } from "react-toastify";
import Extract from "./components/Extract";

function App() {

  const [type, setType] = useState(null);

  const options = [
    {
      name: "embed message",
      image: embed,
      type: "embed"
    },
    {
      name: "extract message",
      image: extract,
      type: "extract"
    },
    {
      name: "Embed message",
      image: embed,
      type: embed
    },
  ]

  return (
    <>
      {
        type === 'embed' && <Embed setType={setType} />
      }
      {
        type === 'extract' && <Extract setType={setType} />
      }
      <main className="w-screen relative h-screen flex items-center justify-center gap-24">
        {
          options.map((option, index) => (
            <div className="cursor-pointer w-1/4 bg-white p-3 px-0 gap-4 flex flex-col items-center justify-between shadow-md hover:shadow-xl transition-all duration-300 hover:scale-[1.03]  border rounded-lg" onClick={() => setType(option.type)} key={index}>
              <img className="w-11/12" src={option.image} alt={option.name} />
              <p className="capitalize text-lg">{option.name}</p>
            </div>
          ))
        }
      </main>
      <ToastContainer />
    </>
  );
}

export default App;
