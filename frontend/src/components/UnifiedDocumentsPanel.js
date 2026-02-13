/**
 * UnifiedDocumentsPanel - Painel Unificado de Documentos
 * Combina:
 * - Upload de ficheiros (S3)
 * - Links externos (Drive, OneDrive, SharePoint, etc.)
 */
import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Upload, Link2, FolderOpen } from "lucide-react";
import S3FileManager from "./S3FileManager";
import OneDriveLinks from "./OneDriveLinks";

const UnifiedDocumentsPanel = ({ processId, clientName }) => {
  const [activeTab, setActiveTab] = useState("files");

  return (
    <div className="space-y-2">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 h-8">
          <TabsTrigger value="files" className="text-xs gap-1.5">
            <Upload className="h-3.5 w-3.5" />
            Ficheiros
          </TabsTrigger>
          <TabsTrigger value="links" className="text-xs gap-1.5">
            <Link2 className="h-3.5 w-3.5" />
            Links Drive
          </TabsTrigger>
        </TabsList>

        <TabsContent value="files" className="mt-3">
          <S3FileManager 
            processId={processId}
            clientName={clientName}
          />
        </TabsContent>

        <TabsContent value="links" className="mt-3">
          <OneDriveLinks 
            processId={processId} 
            clientName={clientName} 
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default UnifiedDocumentsPanel;
