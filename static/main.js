document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".preview-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const table = btn.dataset.name;
      const row = document.getElementById(`preview-${table}`);
      const content = row.querySelector(".preview-content");
      if (row.style.display === "none") {
        if (!content.dataset.loaded) {
          const res = await fetch(`/insight/preview_table/${table}`);
          const html = await res.text();
          content.innerHTML = html;
          content.dataset.loaded = "true";
        }
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  });

  document.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const table = btn.dataset.name;
      if (confirm(`Delete table '${table}'?`)) {
        const res = await fetch(`/insight/delete_table/${table}`, { method: "DELETE" });
        if (res.ok) location.reload();
        else alert("Failed to delete table.");
      }
    });
  });
});
