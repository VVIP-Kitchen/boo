package llm

func detectMimeType(b64 string) string {
	var signatures = map[string]string{
		"JVBERi0":     "application/pdf",
		"R0lGODdh":    "image/gif",
		"R0lGODlh":    "image/gif",
		"iVBORw0KGgo": "image/png",
		"/9j/":        "image/jpg",
	}

	for sig, mime := range signatures {
		if len(b64) >= len(sig) && b64[:len(sig)] == sig {
			return mime
		}
	}
	return ""
}
