document.addEventListener("DOMContentLoaded", function () {
  console.log("Admin Panel initialized");


  initializeNotifications();
});

function initializeNotifications() {

  const notificationBtn = document.querySelector(".notification-btn");

  if (notificationBtn) {
    notificationBtn.addEventListener("click", function () {
      alert("Уведомления: 1 непрочитанное сообщение");
    });
  }
}
