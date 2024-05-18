#include "../music_utility.h"
#include "srsr.h"

/* The domain for SRSR must be names of functions whose
   function calls will be mutated. */

std::vector<const ValueDecl*> VD_refs_srsr;
bool SRSR::ValidateDomain(const std::set<std::string> &domain)
{
  return true;
}

bool SRSR::ValidateRange(const std::set<std::string> &range)
{
  // for (auto e: range)
 //    if (!IsValidVariableName(e))
 //      return false;

  return true;
}

void SRSR::setRange(std::set<std::string> &range) {}

// Return True if the mutant operator can mutate this expression
bool SRSR::IsMutationTarget(clang::Stmt *s, MusicContext *context)
{
  if (isa<DeclStmt>(s) || isa<NullStmt>(s))
    return false;

  const Stmt* parent = GetParentOfStmt(s, context->comp_inst_);

  if (!parent)
    return false;

  if (!isa<CompoundStmt>(parent))
    return false;

  SourceManager &src_mgr = context->comp_inst_->getSourceManager();
  SourceLocation start_loc = s->getBeginLoc();
  SourceLocation end_loc = GetLocationAfterSemicolon(
      src_mgr, 
      TryGetEndLocAfterBracketOrSemicolon(s->getEndLoc(), context->comp_inst_));

  return context->IsRangeInMutationRange(SourceRange(start_loc, end_loc));
}

void SRSR::Mutate(clang::Stmt *s, MusicContext *context)
{ 
  // cout << "SRSR:\n" << ConvertToString(s, context->comp_inst_->getLangOpts()) << endl;
  SourceManager &src_mgr = context->comp_inst_->getSourceManager();
  SourceLocation start_loc = s->getBeginLoc();
  SourceLocation end_loc = GetLocationAfterSemicolon(
      src_mgr, 
      TryGetEndLocAfterBracketOrSemicolon(s->getEndLoc(), context->comp_inst_));
  // cout << "cp1\n";
  string token{ConvertToString(s, context->comp_inst_->getLangOpts())};

  bool skip = false;
  SourceLocation start_loc_decl;

  for (auto stmt: (*(context->getSymbolTable()->getReturnStmtList()))[context->getFunctionId()])
  {
    Expr* res = stmt->getRetValue();
    if(res){
      res = res->IgnoreImpCasts();
      // res->dump();
      if (hasDeclRef(res)){
        for(std::size_t i = 0; i < VD_refs_srsr.size(); ++i){
          start_loc_decl = VD_refs_srsr[i]->getBeginLoc();
          string decl_name = VD_refs_srsr[i]->getNameAsString();
          for(auto local_decl: (*(context->getSymbolTable()->getFuncLocalList()))[context->getFunctionId()]){
            string local_decl_name{local_decl->getNameAsString()};
            if(local_decl_name == decl_name && (start_loc < start_loc_decl)){
              skip = true;
            }
            if(CaseStmt* cases = dyn_cast<CaseStmt>(s)){
              SourceLocation case_satrt_loc = cases->getBeginLoc();
              if(local_decl_name == decl_name && (start_loc_decl < case_satrt_loc)){
                // cout<<local_decl_name<<" == "<<decl_name<<endl;
                skip = true;
              }
            }
            if(DefaultStmt* cases = dyn_cast<DefaultStmt>(s)){
              SourceLocation case_satrt_loc = cases->getBeginLoc();
              if(local_decl_name == decl_name && (start_loc_decl < case_satrt_loc)){
                // cout<<local_decl_name<<" == "<<decl_name<<endl;
                skip = true;
              }
            }
          }
        }
      }
    }
  //need to find way to solve
  //what is exprwithcleanup
    string check = ConvertToString(stmt, context->comp_inst_->getLangOpts());
    if(check.find(".str()") != string::npos){
      return;
    }
    // cout<<"return value: "<< ConvertToString(res, context->comp_inst_->getLangOpts()) <<endl;
    // cout<<"######################"<<endl;
    string mutated_token{ConvertToString(stmt, context->comp_inst_->getLangOpts())};
    if (mutated_token.compare(token) == 0)
      continue;
    // cout<<"skip: "<<skip<<" expr: "<< token<<endl;
    if(!skip)
    {context->mutant_database_.AddMutantEntry(context->getStmtContext(),
        name_, start_loc, end_loc, token, mutated_token, 
        context->getStmtContext().getProteumStyleLineNum());}
  }    

  // cout << "SRSR: end\n";
}

void SRSR::collectDeclRefExprs(Stmt const* stmt) {
  if (stmt) {
    if (DeclRefExpr const* dre = dyn_cast<DeclRefExpr>(stmt)) {
      const ValueDecl* decl = dre->getDecl();
      VD_refs_srsr.push_back(decl);
    }
    for (const Stmt* childStmt : stmt->children()) {
      collectDeclRefExprs(childStmt);
    }
  }
}

bool SRSR::hasDeclRef(Stmt const* stmt) {

  if (!VD_refs_srsr.empty()) {
    // Print or process the collected declarations as needed
    VD_refs_srsr.clear();
  }

  collectDeclRefExprs(stmt);

  if (!VD_refs_srsr.empty()) {
    // Print or process the collected declarations as needed
    for (const ValueDecl* decl : VD_refs_srsr) {
      // decl->dump();
    }
    return true;
  }

  return false;
}