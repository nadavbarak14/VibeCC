import { Link } from "react-router-dom";

export function Header() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
        <Link to="/" className="text-lg font-bold text-gray-900">
          VibeCC
        </Link>
      </div>
    </header>
  );
}
