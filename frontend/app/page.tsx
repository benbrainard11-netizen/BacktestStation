import { redirect } from "next/navigation";

/**
 * Root route — Inbox is the new home page.
 * The old Overview tile cluster has been folded into the Inbox header.
 */
export default function RootPage() {
  redirect("/inbox");
}
