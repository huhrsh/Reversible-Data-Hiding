import { useState } from "react";
import close from "../assets/x-mark.png"
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export default function Embed({ setType }) {
    const [image, setImage] = useState(null);
    const [message, setMessage] = useState("");
    const [imageUrl, setImageUrl] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const size = 260;
    const length = 200;

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file && file.type.startsWith("image/")) {
            const img = new Image();
            img.onload = () => {
                if (img.width <= size && img.height <= size) {
                    setImage(file);
                } else {
                    toast.error(`Image size should be ${size} x ${size} pixels or less.`);
                }
            };
            img.src = URL.createObjectURL(file);
        } else {
            toast.error("Please upload a valid image.");
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!image) {
            toast.error("Please upload an image.");
            return;
        }
        if (message.length === 0 || message.length > length) {
            toast.error(`Message length should be between 1 and ${length} characters.`);
            return;
        }

        const formData = new FormData();
        formData.append("file", image);
        formData.append("message", message.toString());

        setIsLoading(true);

        try {
            const response = await fetch("http://127.0.0.1:8000/embed/", {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error("Failed to encode message.");
            }
            // const data = await response.json();
            // toast.success("Message encoded successfully!");
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);

            // Create a temporary link element to trigger the download
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "encoded_image.png"); // Specify the file name
            document.body.appendChild(link);
            link.click();

            // Clean up after download
            link.parentNode.removeChild(link);
            window.URL.revokeObjectURL(url);
            toast.success("Message encoded and image downloaded successfully!");
            setImage();
            setMessage();
            setType();
        } catch (error) {
            toast.error(error.message || "An error occurred during encoding.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed top-0 left-0 z-50 bg-neutral-100 bg-opacity-85 w-screen h-screen animate__animated animate__slideInDown animate__fast flex items-center justify-center">
            <div className="aspect-video h-[57%] shadow-lg bg-white rounded-lg border p-6 relative flex flex-col gap-4">

                <button onClick={() => setType()} className="absolute top-0 right-0 translate-x-[50%] -translate-y-[50%] transition-all duration-300 hover:bg-red-600 hover:shadow-md bg-red-500 rounded-full p-2.5">
                    <img className='h-5 invert ' src={close} alt="close" />
                </button>

                <h1 className="text-3xl font-bold leading-snug bg-gradient-to-tr w-fit from-blue-600 to-sky-500 text-transparent bg-clip-text">Encode Message</h1>
                <form onSubmit={handleSubmit}>
                    <div className="mb-4 flex flex-col">
                        <label className="font-medium text-gray-700 text-base">
                            Upload Image <span className="text-sm text-neutral-500 font-medium">({size}x{size} px max)</span>
                        </label>
                        <input
                            type="file"
                            accept="image/*"
                            onChange={handleImageChange}
                            className="mt-2"
                        />
                    </div>
                    <div className="mb-4 flex flex-col">
                        <label className="font-medium text-gray-700 text-base">
                            Message <span className="text-sm text-neutral-500 font-medium">(1-{length} characters)</span>
                        </label>
                        <textarea
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            className="mt-2 p-2 w-full border rounded-lg outline-none focus-within:shadow-md transition-all duration-300"
                            rows="3"
                        ></textarea>
                    </div>
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="px-4 py-2 bg-gradient-to-tr w-fit from-blue-600 to-sky-500 text-white rounded-lg"
                    >
                        {isLoading ? "Encoding..." : "Encode"}
                    </button>
                </form>
                {imageUrl && (
                    <div className="mt-4">
                        <h3>Encoded Image:</h3>
                        <img src={imageUrl} alt="Encoded" />
                    </div>
                )}
            </div>
        </div>
    );
}
