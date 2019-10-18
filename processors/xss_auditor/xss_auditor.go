package main

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"strings"

	"github.com/jbowtie/gokogiri"
)

const (
	connHost = "localhost"
	connPort = "5127"
	connType = "tcp"
)

// RequestPacket contains
type RequestPacket struct {
	URL  string `json:"url"`
	Body string `json:"body"`
}

// AuditPackage contains parsed json data from xss_watcher
type AuditPackage struct {
	ItsResponse string        `json:"res_body"`
	ItsRequest  RequestPacket `json:"req_packet"`
}

var safeJavaScriptURL = []string{"javascript:void(0)"}
var extContentAttrs = []string{"src", "code", }
var eventHandlerAttrs = []string{"onload", "onerror", "onclick", "oncut", "onunload", "onfocus", "onblur"}


func main() {
	// Listen for incoming connections.
	l, err := net.Listen(connType, connHost+":"+connPort)
	if err != nil {
		fmt.Println("Error listening:", err.Error())
		os.Exit(1)
	}
	// Close the listener when the application closes.
	defer l.Close()
	fmt.Println("Listening on " + connHost + ":" + connPort)

	for {
		// Listen for an incoming connection.
		conn, err := l.Accept()
		if err != nil {
			fmt.Println("Error accepting: ", err.Error())
			os.Exit(1)
		}
		// Handle connections in a new goroutine.
		go handleRequest(conn)
	}
}

func containsIgnoreCase(a_string, a_substring string) bool {
	return strings.Contains(strings.ToLower(a_string), strings.ToLower(a_substring))
}

func compareWithRequest(afterParse string, originalRequest RequestPacket) bool {
	// ADDME: perform data transformation here (to prevent obfuscation)
	// fmt.Println(afterParse, originalRequest.URL)
	// fmt.Println(afterParse, originalRequest.Body)
	return containsIgnoreCase(originalRequest.URL, afterParse) || containsIgnoreCase(originalRequest.Body, afterParse)
}

func stringInSlice(a string, list []string) bool {
	for _, b := range list {
		if b == a {
			return true
		}
	}
	return false
}

func getPossiblyDangerousHundredCharacters(a string) string {
	if commentIndex := strings.IndexByte(a, '//'); commentIndex >= 0
		return a[:commentIndex]
	else if len(a) >= 100
		return a[:100]
	return a
}

func isJavascriptUrl(a string) bool {
	return strings.HasPrefix(a, "javascript:")
}

func handleRequest(conn net.Conn) {
	// buf := make([]byte, 65535)
	// _, err := conn.Read(buf)

	d := json.NewDecoder(conn)

	var audit AuditPackage

	err := d.Decode(&audit)
	// fmt.Println(audit.ItsRequest, err)
	// fmt.Println(audit.ItsResponse, err)

	if err != nil {
		fmt.Println("Error reading:", err.Error())
	}

	doc, err := gokogiri.ParseHtml([]byte(audit.ItsResponse))

	if err != nil {
		fmt.Println("Parsing has error:", err)
		return
	}

	// fmt.Println(doc.String())

	rootParse, _ := doc.Root().Search(".//*")
	for _, s := range rootParse {
		// --- Find <script> tags
		inlineScriptTags, _ := s.Search("//script")
		for _, scriptTag := range inlineScriptTags {
			// --- Check Inline Script Tags
			// the Auditor checks whether the content of the script is contained within the request 
			scriptInnerHTML := scriptTag.InnerHtml()
			if scriptInnerHTML != "" {
				// fmt.Println(i, scriptInnerHTML)
				var hundredCharacters = getPossiblyDangerousHundredCharacters(scriptInnerHTML)
				if compareWithRequest(hundredCharacters, audit.ItsRequest) {
					fmt.Println("DETECTED1!")
				}
			}
		}

		// --- Check Dangerous HTML Attributes
		for _, attr := range s.Attributes() {
			// 1. checks whether the attribute contains a JavaScript URL
			// 2. whether the attribute is an event handler
			// 3. and if the complete attribute (content?) is contained in the request 
			attrValue := s.Attr(attr)
			if stringInSlice(atrr.String(), eventHandlerAttrs) || isJavascriptUrl(attrValue) {
				if compareWithRequest(attrValue, AuditPackage.ItsRequest) {
					fmt.Println("DETECTED2!")
				}
			}
		}

		// --- Check External Content (Specific Tags)



	}

	conn.Write([]byte("doc"))
	conn.Close()

	doc.Free()
}

// echo -n "<html><body onload=javascript:alert(1)><div><h1></div>" | nc localhost 5127
// nc localhost 5127 < example.html
