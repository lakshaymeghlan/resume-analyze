import { useState, useRef } from "react";
import "@/App.css";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { FileText, Sparkles, CheckCircle2, XCircle, TrendingUp, Loader2, Upload, X } from "lucide-react";
import { toast, Toaster } from "sonner";

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const API = `${BACKEND_URL.replace(/\/$/, '')}/api`; // remove trailing slash if any
console.log('Using API base:', API);

function App() {
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("upload");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
      toast.error("Please upload a PDF file");
      return;
    }

    setUploadLoading(true);
    setUploadedFile(file);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API}/upload-resume`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setResumeText(response.data.text);
      toast.success("Resume uploaded successfully!");
    } catch (error) {
      console.error("Upload error:", error);
      toast.error(error.response?.data?.detail || "Failed to upload resume");
      setUploadedFile(null);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setResumeText("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleAnalyze = async () => {
    if (!resumeText.trim() || !jobDescription.trim()) {
      toast.error("Please upload resume and enter job description");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/analyze`, {
        resume_text: resumeText,
        job_description: jobDescription
      });
      setAnalysis(response.data);
      setActiveTab("results");
      toast.success("Analysis complete!");
    } catch (error) {
      console.error("Analysis error:", error);
      toast.error(error.response?.data?.detail || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return "Excellent Match";
    if (score >= 60) return "Good Match";
    if (score >= 40) return "Fair Match";
    return "Needs Improvement";
  };

  return (
    <div className="App">
      <Toaster position="top-center" richColors />
      
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <Sparkles className="icon" />
            <span>AI-Powered ATS Optimization</span>
          </div>
          <h1 className="hero-title">Smart Resume & Job Matcher</h1>
          <p className="hero-subtitle">
            Analyze your resume against job descriptions, get instant match scores,
            and receive AI-powered suggestions to optimize your application.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-container">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="tabs-container">
          <TabsList className="tabs-list">
            <TabsTrigger value="upload" data-testid="upload-tab">
              <FileText className="tab-icon" />
              Upload & Analyze
            </TabsTrigger>
            <TabsTrigger value="results" disabled={!analysis} data-testid="results-tab">
              <TrendingUp className="tab-icon" />
              Results
            </TabsTrigger>
          </TabsList>

          {/* Upload Tab */}
          <TabsContent value="upload" className="tab-content">
            <div className="upload-grid">
              <Card className="upload-card">
                <CardHeader>
                  <CardTitle>Your Resume</CardTitle>
                  <CardDescription>Upload your resume as a PDF file</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="file-upload-container">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf"
                      onChange={handleFileUpload}
                      className="file-input-hidden"
                      id="resume-upload"
                      data-testid="resume-file-input"
                    />
                    
                    {!uploadedFile ? (
                      <label htmlFor="resume-upload" className="file-upload-label" data-testid="upload-area">
                        <div className="upload-icon-container">
                          {uploadLoading ? (
                            <Loader2 className="upload-icon animate-spin" />
                          ) : (
                            <Upload className="upload-icon" />
                          )}
                        </div>
                        <div className="upload-text">
                          <p className="upload-title">
                            {uploadLoading ? "Processing PDF..." : "Click to upload PDF"}
                          </p>
                          <p className="upload-subtitle">
                            or drag and drop your resume here
                          </p>
                          <p className="upload-format">PDF format only</p>
                        </div>
                      </label>
                    ) : (
                      <div className="uploaded-file-card" data-testid="uploaded-file-card">
                        <div className="file-info">
                          <FileText className="file-icon" />
                          <div className="file-details">
                            <p className="file-name">{uploadedFile.name}</p>
                            <p className="file-size">
                              {(uploadedFile.size / 1024).toFixed(2)} KB
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={handleRemoveFile}
                          className="remove-file-btn"
                          data-testid="remove-file-button"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    )}
                    
                    {resumeText && (
                      <div className="extracted-preview">
                        <p className="preview-label">Extracted Text Preview:</p>
                        <div className="preview-text">
                          {resumeText.substring(0, 300)}...
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="upload-card">
                <CardHeader>
                  <CardTitle>Job Description</CardTitle>
                  <CardDescription>Paste the job description you're targeting</CardDescription>
                </CardHeader>
                <CardContent>
                  <Textarea
                    data-testid="job-description-input"
                    placeholder="Paste job description here...\n\nExample:\nWe're looking for a Full Stack Developer with:\n- 3+ years of experience\n- Strong skills in React, Node.js, Python\n- Experience with AWS and Docker\n- Knowledge of CI/CD pipelines...\n"
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                    className="job-textarea"
                  />
                </CardContent>
              </Card>
            </div>

            <div className="analyze-button-container">
              <Button
                data-testid="analyze-button"
                onClick={handleAnalyze}
                disabled={loading}
                className="analyze-button"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin mr-2" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2" />
                    Analyze Match
                  </>
                )}
              </Button>
            </div>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results" className="tab-content">
            {analysis && (
              <div className="results-container">
                {/* Score Card */}
                <Card className="score-card">
                  <CardContent className="score-content">
                    <div className="score-circle">
                      <div className="score-number">
                        <span className={`score-value ${getScoreColor(analysis.match_score)}`}>
                          {analysis.match_score}
                        </span>
                        <span className="score-label">/ 100</span>
                      </div>
                      <Progress value={analysis.match_score} className="score-progress" />
                    </div>
                    <div className="score-info">
                      <h3 className="score-title">{getScoreLabel(analysis.match_score)}</h3>
                      <p className="score-description">
                        Your resume matches {analysis.match_score}% of the job requirements
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Skills Analysis */}
                <div className="skills-grid">
                  <Card className="skills-card">
                    <CardHeader>
                      <CardTitle className="skills-title">
                        <CheckCircle2 className="text-green-600" />
                        Matched Skills
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="skills-badges">
                        {analysis.matched_skills.length > 0 ? (
                          analysis.matched_skills.map((skill, idx) => (
                            <Badge key={idx} variant="default" className="skill-badge matched">
                              {skill}
                            </Badge>
                          ))
                        ) : (
                          <p className="text-gray-500">No matched skills found</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="skills-card">
                    <CardHeader>
                      <CardTitle className="skills-title">
                        <XCircle className="text-red-600" />
                        Missing Skills
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="skills-badges">
                        {analysis.missing_skills.length > 0 ? (
                          analysis.missing_skills.map((skill, idx) => (
                            <Badge key={idx} variant="destructive" className="skill-badge missing">
                              {skill}
                            </Badge>
                          ))
                        ) : (
                          <p className="text-gray-500">No missing skills</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Suggestions */}
                <Card className="suggestions-card">
                  <CardHeader>
                    <CardTitle>Improvement Suggestions</CardTitle>
                    <CardDescription>AI-powered recommendations to boost your match score</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="suggestions-list">
                      {analysis.suggestions.map((suggestion, idx) => (
                        <li key={idx} className="suggestion-item">
                          <div className="suggestion-number">{idx + 1}</div>
                          <span className="suggestion-text">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                {/* Rewritten Resume */}
                <Card className="rewritten-card">
                  <CardHeader>
                    <CardTitle>Optimized Resume</CardTitle>
                    <CardDescription>ATS-optimized version of your resume</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="rewritten-content">
                      <pre className="rewritten-text">{analysis.rewritten_resume}</pre>
                    </div>
                  </CardContent>
                </Card>

                {/* New Analysis Button */}
                <div className="new-analysis-container">
                  <Button
                    data-testid="new-analysis-button"
                    onClick={() => {
                      setActiveTab("upload");
                      setAnalysis(null);
                      setUploadedFile(null);
                      setResumeText("");
                      setJobDescription("");
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                    variant="outline"
                    className="new-analysis-button"
                  >
                    <FileText className="mr-2" />
                    New Analysis
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;