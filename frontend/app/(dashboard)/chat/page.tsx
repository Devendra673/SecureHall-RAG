import { redirect } from 'next/navigation';

// The full chat UI lives on the root page (/)
// This redirect keeps the /chat URL working for the proxy middleware
export default function ChatPage() {
  redirect('/');
}
