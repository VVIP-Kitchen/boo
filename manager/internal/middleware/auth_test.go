package middleware

import (
"net/http"
"net/http/httptest"
"testing"

"github.com/gin-gonic/gin"
)

func TestAuthMiddleware(t *testing.T) {
gin.SetMode(gin.TestMode)

router := gin.New()
router.Use(NewAuthMiddleware("secret"))
router.GET("/protected", func(c *gin.Context) {
c.JSON(http.StatusOK, gin.H{"ok": true})
})

req, _ := http.NewRequest(http.MethodGet, "/protected", nil)
resp := httptest.NewRecorder()
router.ServeHTTP(resp, req)
if resp.Code != http.StatusUnauthorized {
t.Fatalf("expected 401 for missing header, got %d", resp.Code)
}

req, _ = http.NewRequest(http.MethodGet, "/protected", nil)
req.Header.Set("Authorization", "Bearer wrong")
resp = httptest.NewRecorder()
router.ServeHTTP(resp, req)
if resp.Code != http.StatusUnauthorized {
t.Fatalf("expected 401 for wrong token, got %d", resp.Code)
}

req, _ = http.NewRequest(http.MethodGet, "/protected", nil)
req.Header.Set("Authorization", "Bearer secret")
resp = httptest.NewRecorder()
router.ServeHTTP(resp, req)
if resp.Code != http.StatusOK {
t.Fatalf("expected 200 for valid token, got %d", resp.Code)
}
}
