
//#include "art/Framework/Services/Registry/ServiceHandle.h"
//#include "art/Framework/Services/Optional/TFileService.h"
//#include "art/Framework/Services/Optional/TFileDirectory.h"

//#include "Geometry/Geometry.h"

#include "PhotonLibrary.h"
#include "PhotonVoxels.h"
#include <iostream>
#include <stdexcept>
//#include "messagefacility/MessageLogger/MessageLogger.h"

#include "TFile.h"
#include "TTree.h"
#include "TKey.h"

namespace phot{

  std::vector<float> PhotonLibrary::EmptyChannelsList; // used for invalid return value

  //------------------------------------------------------------

  PhotonLibrary::PhotonLibrary()
  {
    fLookupTable.clear();
  }


  //------------------------------------------------------------

  PhotonLibrary::~PhotonLibrary()
  {
    fLookupTable.clear();
  }

  //------------------------------------------------------------

  void PhotonLibrary::StoreLibraryToFile(std::string LibraryFile)
  {
    std::cout << "Writing photon library to input file: " << LibraryFile.c_str()<<std::endl;

    TFile fout(LibraryFile.c_str(),"RECREATE");

    TTree *tt = new TTree("PhotonLibraryData","PhotonLibraryData");

    Int_t     Voxel;
    Int_t     OpChannel;
    Float_t   Visibility;


    tt->Branch("Voxel",      &Voxel,      "Voxel/I");
    tt->Branch("OpChannel",  &OpChannel,  "OpChannel/I");
    tt->Branch("Visibility", &Visibility, "Visibility/F");


    for(size_t ivox=0; ivox!=fLookupTable.size(); ++ivox)
      {
	for(size_t ichan=0; ichan!=fLookupTable.at(ivox).size(); ++ichan)
	  {
	    if(fLookupTable[ivox].at(ichan) > 0)
	      {
		Voxel      = ivox;
		OpChannel  = ichan;
		Visibility = fLookupTable[ivox][ichan];
		tt->Fill();
	      }
	  }
      }
    fout.cd();
    tt->Write();
    fout.Close();
  }


  //------------------------------------------------------------

  void PhotonLibrary::CreateEmptyLibrary( size_t NVoxels, size_t NOpChannels)
  {
    fLookupTable.clear();

    fNVoxels     = NVoxels;
    fNOpChannels = NOpChannels;

    fLookupTable.resize(NVoxels);

    for(size_t ivox=0; ivox!=NVoxels; ivox++)
      {
        fLookupTable[ivox].resize(NOpChannels,0);
      }
  }


  //------------------------------------------------------------

  void PhotonLibrary::LoadLibraryFromFile(std::string LibraryFile, size_t NVoxels)
  {
    fLookupTable.clear();

    std::cout<< "Reading photon library from input file: " << LibraryFile.c_str()<<std::endl;

    TFile *f = nullptr;
    TTree *tt = nullptr;

    f  =  TFile::Open(LibraryFile.c_str());
    if(!f || f->IsZombie()) {
      if(f) {
        f->Close();
        delete f;
      }
      std::cerr<<"\033[95m<<"<<__FUNCTION__<<">>\033[00m " << "Failed to open a ROOT file: " << LibraryFile.c_str()<<std::endl;
      std::cerr<<"If you don't have photon library data file, download from below URL..."<<std::endl;
      std::cerr<<"/cvmfs/icarus.opensciencegrid.org/products/icarus/icarus_data/v10_06_03/icarus_data/PhotonLibrary/PhotonLibrary-20201209.root"<<std::endl<<std::endl;
      throw std::runtime_error("Failed to open photon library file: " + LibraryFile);
    }

    tt = dynamic_cast<TTree*>(f->Get("PhotonLibraryData"));
    if (!tt) { // Library not in the top directory
      TKey *key = f->FindKeyAny("PhotonLibraryData");
      if (key) tt = dynamic_cast<TTree*>(key->ReadObj());
    }
    if (!tt) {
      std::cerr << "PhotonLibraryData not found in file " << LibraryFile << std::endl;
      f->Close();
      delete f;
      throw std::runtime_error("PhotonLibraryData tree not found in photon library file: " + LibraryFile);
    }
    if (!tt->GetBranch("Voxel") ||
        !tt->GetBranch("OpChannel") ||
        !tt->GetBranch("Visibility")) {
      std::cerr << "PhotonLibraryData in file " << LibraryFile
                << " is missing one of the required branches: "
                << "Voxel, OpChannel, Visibility" << std::endl;
      f->Close();
      delete f;
      throw std::runtime_error("Invalid photon library tree in file: " + LibraryFile);
    }

    Int_t     Voxel;
    Int_t     OpChannel;
    Float_t   Visibility;

    tt->SetBranchAddress("Voxel",      &Voxel);
    tt->SetBranchAddress("OpChannel",  &OpChannel);
    tt->SetBranchAddress("Visibility", &Visibility);




    fNVoxels     = NVoxels;
    fNOpChannels = 1;      // Minimum default, overwritten by library reading


    fLookupTable.resize(NVoxels);


    size_t NEntries = tt->GetEntries();

    for(size_t i=0; i!=NEntries; ++i) {
      tt->GetEntry(i);

      // Set # of optical channels to 1 more than largest one seen
      if (Voxel < 0 || Voxel >= (int)fNVoxels || OpChannel < 0) {
        f->Close();
        delete f;
        throw std::runtime_error("Photon library entry has out-of-range voxel/channel index in file: " + LibraryFile);
      }

      if (OpChannel >= (int)fNOpChannels)
        fNOpChannels = OpChannel+1;

      // Expand this voxel's vector if needed
      if (fLookupTable[Voxel].size() < fNOpChannels)
        fLookupTable[Voxel].resize(fNOpChannels, 0);

      // Set the visibility at this optical channel
      fLookupTable[Voxel][OpChannel] = Visibility;
    }

    // Go through the table and fill in any missing 0's
    for(size_t ivox=0; ivox!=NVoxels; ivox++)
    {
      if (fLookupTable[ivox].size() < fNOpChannels)
	fLookupTable[ivox].resize(fNOpChannels,0);
    }


    std::cout <<  NVoxels << " voxels,  " << fNOpChannels<<" channels" <<std::endl;


    try
      {
        f->Close();
      }
    catch(...)
      {
        std::cerr << "Error in closing file : " << LibraryFile.c_str()<<std::endl;
      }
    delete f;
  }

  //----------------------------------------------------

  float PhotonLibrary::GetCount(size_t Voxel, size_t OpChannel)
  {
    //if(/*(Voxel<0)||*/(Voxel>=fNVoxels)||/*(OpChannel<0)||*/(OpChannel>=fNOpChannels))
    //  return 0;
    //else
      return fLookupTable[Voxel][OpChannel];
  }

  //----------------------------------------------------

  void PhotonLibrary::SetCount(size_t Voxel, size_t OpChannel, float Count)
  {
    if(/*(Voxel<0)||*/(Voxel>=fNVoxels))
      std::cerr <<"Error - attempting to set count in voxel " << Voxel<<" which is out of range" <<std::endl;
    else
      fLookupTable[Voxel].at(OpChannel) = Count;
  }

  //----------------------------------------------------

  const std::vector<float>* PhotonLibrary::GetCounts(size_t Voxel) const
  {
    if(/*(Voxel<0)||*/(Voxel>=fNVoxels))
      return EmptyList(); // FIXME!!! better to throw an exception!
    else
      return &(fLookupTable[Voxel]);
  }



}
